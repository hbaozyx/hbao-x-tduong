import os
import asyncio
import logging
import time

import discord
from discord.ext import commands, tasks

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('voice_keeper')

TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['VOICE_CHANNEL_ID'])

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)
voice_lock = asyncio.Lock()
failures = 0
next_attempt = 0.0


async def ensure_voice():
    global failures, next_attempt
    if time.monotonic() < next_attempt:
        return
    async with voice_lock:
        if time.monotonic() < next_attempt or not bot.is_ready():
            return
        try:
            channel = bot.get_channel(CHANNEL_ID)
            if channel is None:
                channel = await bot.fetch_channel(CHANNEL_ID)
            if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                log.error('VOICE_CHANNEL_ID is not a voice or stage channel')
                next_attempt = time.monotonic() + 300
                return
            me = channel.guild.me
            if me is not None and not channel.permissions_for(me).connect:
                log.error('Bot lacks Connect permission for %s', channel.name)
                next_attempt = time.monotonic() + 300
                return

            vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
            if vc is not None and vc.is_connected():
                if vc.channel and vc.channel.id == CHANNEL_ID:
                    failures = 0
                    next_attempt = 0.0
                    return
                log.info('Moving voice connection to %s', channel.name)
                await asyncio.wait_for(vc.move_to(channel), timeout=65)
            else:
                if vc is not None:
                    try:
                        await asyncio.wait_for(vc.disconnect(force=True), timeout=12)
                    except Exception:
                        log.warning('Could not fully clean up old voice connection', exc_info=True)
                log.info('Connecting to voice channel %s (%s)', channel.name, CHANNEL_ID)
                await channel.connect(self_deaf=True, reconnect=True, timeout=60)
            failures = 0
            next_attempt = 0.0
            log.info('Voice connected: %s', channel.name)
        except (discord.DiscordException, asyncio.TimeoutError, OSError) as exc:
            failures += 1
            delay = min(15 * (2 ** min(failures - 1, 4)), 240)
            next_attempt = time.monotonic() + delay
            log.warning('Voice connection failed (%s). Retrying in %s seconds', type(exc).__name__, delay, exc_info=True)
        except Exception:
            failures += 1
            next_attempt = time.monotonic() + 60
            log.exception('Unexpected voice error; retrying in 60 seconds')


@tasks.loop(seconds=15)
async def voice_watchdog():
    await ensure_voice()


@voice_watchdog.before_loop
async def before_watchdog():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    log.info('Logged in as %s', bot.user)
    if not voice_watchdog.is_running():
        voice_watchdog.start()


@bot.event
async def on_voice_state_update(member, before, after):
    if bot.user and member.id == bot.user.id:
        if after.channel is None or after.channel.id != CHANNEL_ID:
            log.warning('Bot left target voice channel; watchdog will reconnect')
            global next_attempt
            next_attempt = 0.0


if __name__ == '__main__':
    bot.run(TOKEN, reconnect=True)

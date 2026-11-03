import asyncio
import logging
import os

import discord
from discord.ext import commands, tasks

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('room247')

TOKEN = os.getenv('DISCORD_TOKEN', '').strip()
CHANNEL_ID_RAW = os.getenv('VOICE_CHANNEL_ID', '').strip()
if not TOKEN:
    raise RuntimeError('Missing DISCORD_TOKEN in Railway Variables')
if not CHANNEL_ID_RAW.isdigit():
    raise RuntimeError('VOICE_CHANNEL_ID must be a numeric Discord voice channel ID')
CHANNEL_ID = int(CHANNEL_ID_RAW)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)
voice_lock = asyncio.Lock()


async def ensure_connected():
    # Only the watchdog initiates voice connections. Never connect directly
    # from voice state events, which may fire during a handshake/disconnect.
    if not bot.is_ready():
        return
    async with voice_lock:
        try:
            channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
            if not isinstance(channel, discord.VoiceChannel):
                log.error('VOICE_CHANNEL_ID %s is not a standard voice channel', CHANNEL_ID)
                return

            vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
            if vc and vc.is_connected():
                if vc.channel and vc.channel.id == CHANNEL_ID:
                    return
                log.warning('Bot is in %s; moving to configured channel', vc.channel)
                await vc.move_to(channel)
                return

            if vc:
                log.warning('Cleaning up disconnected voice client before reconnect')
                try:
                    await asyncio.wait_for(vc.disconnect(force=True), timeout=15)
                except (asyncio.TimeoutError, Exception) as exc:
                    log.warning('Voice cleanup error: %r', exc)

            log.info('Connecting to voice channel %s (%s)', channel.name, CHANNEL_ID)
            await channel.connect(timeout=30, reconnect=True, self_deaf=True)
            log.info('Voice connection established: %s (%s)', channel.name, CHANNEL_ID)
        except discord.Forbidden:
            log.exception('Missing View Channel or Connect permission')
        except Exception:
            log.exception('Voice connection attempt failed; next watchdog cycle will retry')


@tasks.loop(seconds=45)
async def voice_watchdog():
    await ensure_connected()


@voice_watchdog.before_loop
async def before_watchdog():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    log.info('Logged in as %s (discord.py %s)', bot.user, discord.__version__)
    if not voice_watchdog.is_running():
        voice_watchdog.start()


@bot.event
async def on_voice_state_update(member, before, after):
    # Log only. The watchdog reconnects at a controlled pace.
    if bot.user and member.id == bot.user.id:
        if after.channel is None and before.channel is not None:
            log.warning('Voice disconnected from %s; waiting for watchdog', before.channel)
        elif after.channel and (before.channel is None or before.channel.id != after.channel.id):
            log.info('Voice state changed to %s', after.channel)


bot.run(TOKEN, reconnect=True)

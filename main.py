import asyncio
import logging
import os
import time

import discord
from discord.ext import commands, tasks

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('tduong_voice')
TOKEN = os.environ['DISCORD_TOKEN'].strip()
CHANNEL_ID = int(os.environ['VOICE_CHANNEL_ID'])

class VoiceKeeper(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.default())
        self.voice_lock = asyncio.Lock()
        self.failures = 0
        self.next_attempt = 0.0

    async def setup_hook(self):
        self.watchdog.start()

    async def ensure_voice(self):
        if time.monotonic() < self.next_attempt or not self.is_ready():
            return
        async with self.voice_lock:
            if time.monotonic() < self.next_attempt or not self.is_ready():
                return
            try:
                channel = self.get_channel(CHANNEL_ID) or await self.fetch_channel(CHANNEL_ID)
                if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                    log.error('INVALID_CHANNEL id=%s', CHANNEL_ID)
                    self.next_attempt = time.monotonic() + 300
                    return
                me = channel.guild.me
                if me and not channel.permissions_for(me).connect:
                    log.error('MISSING_CONNECT_PERMISSION channel=%s', CHANNEL_ID)
                    self.next_attempt = time.monotonic() + 300
                    return
                vc = discord.utils.get(self.voice_clients, guild=channel.guild)
                if vc and vc.is_connected():
                    if vc.channel and vc.channel.id == CHANNEL_ID:
                        self.failures = 0
                        self.next_attempt = 0
                        return
                    log.warning('VOICE_MOVED returning_to=%s', CHANNEL_ID)
                    await asyncio.wait_for(vc.move_to(channel), timeout=35)
                else:
                    if vc:
                        try:
                            await asyncio.wait_for(vc.disconnect(force=True), timeout=12)
                        except Exception:
                            log.exception('VOICE_CLEANUP_FAILED')
                    log.info('VOICE_JOIN_ATTEMPT channel=%s', CHANNEL_ID)
                    await asyncio.wait_for(
                        channel.connect(self_deaf=True, reconnect=True, timeout=30),
                        timeout=75,
                    )
                self.failures = 0
                self.next_attempt = 0
                log.info('VOICE_CONNECTED channel=%s', CHANNEL_ID)
            except (discord.DiscordException, asyncio.TimeoutError, OSError) as exc:
                self.failures += 1
                delay = min(15 * 2 ** min(self.failures - 1, 4), 240)
                self.next_attempt = time.monotonic() + delay
                log.warning('VOICE_RETRY error=%s detail=%s wait=%ss', type(exc).__name__, exc, delay, exc_info=True)
            except Exception:
                self.failures += 1
                self.next_attempt = time.monotonic() + 60
                log.exception('VOICE_UNEXPECTED_ERROR retry_in=60s')

    @tasks.loop(seconds=30, reconnect=True)
    async def watchdog(self):
        await self.ensure_voice()

    @watchdog.before_loop
    async def before_watchdog(self):
        await self.wait_until_ready()

    @watchdog.error
    async def watchdog_error(self, error):
        log.error('WATCHDOG_STOPPED: %r', error, exc_info=(type(error), error, error.__traceback__))

bot = VoiceKeeper()

@bot.event
async def on_ready():
    log.info('GATEWAY_READY user=%s discord.py=%s', bot.user, discord.__version__)

@bot.event
async def on_voice_state_update(member, before, after):
    if bot.user and member.id == bot.user.id:
        log.info('VOICE_STATE before=%s after=%s', getattr(before.channel, 'id', None), getattr(after.channel, 'id', None))
        # Do not reset backoff: repeated disconnects must not cause a reconnect storm.

if __name__ == '__main__':
    bot.run(TOKEN, reconnect=True)

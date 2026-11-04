"""Discord voice room keeper for a permanent voice channel on Railway.

Environment: DISCORD_TOKEN, VOICE_CHANNEL_ID
Only run ONE instance with this bot token.
"""
import asyncio
import logging
import os
import time

import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('room247')
TOKEN = os.getenv('DISCORD_TOKEN', '').strip()
CHANNEL_RAW = os.getenv('VOICE_CHANNEL_ID', '').strip()
if not TOKEN:
    raise RuntimeError('Missing DISCORD_TOKEN on Railway')
if not CHANNEL_RAW.isdecimal():
    raise RuntimeError('VOICE_CHANNEL_ID must be a numeric Discord channel ID')
CHANNEL_ID = int(CHANNEL_RAW)
CHECK_SECONDS = 10


class RoomBot(commands.Bot):
    async def setup_hook(self):
        self.voice_lock = asyncio.Lock()
        self.voice_wake = asyncio.Event()
        self.voice_started_at = 0.0
        self.voice_supervisor_task = asyncio.create_task(self.voice_supervisor())

    async def close(self):
        task = getattr(self, 'voice_supervisor_task', None)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await super().close()

    async def resolve_channel(self):
        channel = self.get_channel(CHANNEL_ID)
        if channel is None:
            channel = await self.fetch_channel(CHANNEL_ID)
        if not isinstance(channel, discord.VoiceChannel):
            raise RuntimeError('VOICE_CHANNEL_ID must point to a permanent voice channel')
        return channel

    @staticmethod
    def voice_health(vc):
        if vc is None:
            return False, 'no voice client'
        if not vc.is_connected():
            return False, 'voice client is disconnected'
        # discord.py stores its voice websocket polling task in _runner.
        # Detect crashes such as ConnectionClosed(code=1006) even when the
        # is_connected() flag has not yet been updated. Private API: pin version.
        runner = getattr(vc, '_runner', None)
        if runner is not None and runner.done():
            try:
                exc = runner.exception() if not runner.cancelled() else None
            except Exception as error:
                exc = error
            return False, f'voice websocket poller ended: {exc!r}'
        ws = getattr(vc, 'ws', None)
        if ws is not None:
            closed = getattr(ws, 'closed', False)
            if callable(closed):
                closed = closed()
            if closed:
                return False, 'voice websocket is closed'
        return True, 'voice session healthy'

    async def ensure_voice(self):
        channel = await self.resolve_channel()
        vc = discord.utils.get(self.voice_clients, guild=channel.guild)
        healthy, reason = self.voice_health(vc)
        if healthy:
            if vc.channel is None or vc.channel.id != CHANNEL_ID:
                log.warning('Voice client in wrong channel; moving to %s', CHANNEL_ID)
                await asyncio.wait_for(vc.move_to(channel), timeout=30)
            return

        log.warning('Voice unhealthy: %s', reason)
        if vc is not None:
            try:
                await asyncio.wait_for(vc.disconnect(force=True), timeout=15)
            except Exception:
                log.exception('Unable to clean up old voice client')
        # Discord needs a short interval to retire the old voice session.
        await asyncio.sleep(3)
        log.info('Joining permanent voice channel %s', CHANNEL_ID)
        # Let discord.py retry transient voice websocket failures internally.
        vc = await asyncio.wait_for(
            channel.connect(timeout=30, reconnect=True, self_deaf=True),
            timeout=90,
        )
        self.voice_started_at = time.monotonic()
        log.info('VOICE_CONNECTED channel=%s guild=%s connected=%s',
                 channel.id, channel.guild.id, vc.is_connected())

    async def voice_supervisor(self):
        await self.wait_until_ready()
        failures = 0
        while not self.is_closed():
            try:
                async with self.voice_lock:
                    await self.ensure_voice()
                failures = 0
            except asyncio.CancelledError:
                raise
            except Exception:
                failures += 1
                log.exception('VOICE_SUPERVISOR_ERROR attempt=%d', failures)
            delay = min(90, 5 * 2 ** min(failures, 4)) if failures else CHECK_SECONDS
            try:
                await asyncio.wait_for(self.voice_wake.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            self.voice_wake.clear()


intents = discord.Intents.default()
bot = RoomBot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    log.info('GATEWAY_READY user=%s discord.py=%s', bot.user, discord.__version__)
    bot.voice_wake.set()


@bot.event
async def on_resumed():
    log.info('GATEWAY_RESUMED')
    bot.voice_wake.set()


@bot.event
async def on_voice_state_update(member, before, after):
    if bot.user and member.id == bot.user.id:
        log.info('BOT_VOICE_STATE before=%s after=%s',
                 getattr(before.channel, 'id', None),
                 getattr(after.channel, 'id', None))
        if after.channel is None or after.channel.id != CHANNEL_ID:
            bot.voice_wake.set()


bot.run(TOKEN, reconnect=True)

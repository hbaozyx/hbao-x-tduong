import asyncio
import logging
import os
import time

import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('room247')

TOKEN = os.getenv('DISCORD_TOKEN', '').strip()
raw_id = os.getenv('VOICE_CHANNEL_ID', '').strip()
if not TOKEN:
    raise RuntimeError('Missing DISCORD_TOKEN in Railway Variables')
if not raw_id.isdigit():
    raise RuntimeError('VOICE_CHANNEL_ID must be a numeric Discord voice channel ID')
CHANNEL_ID = int(raw_id)

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
voice_lock = asyncio.Lock()
wake = asyncio.Event()
last_attempt = 0.0

async def ensure_connected():
    global last_attempt
    if not bot.is_ready() or bot.is_closed():
        return
    async with voice_lock:
        # Avoid competing handshakes while Discord is still cleaning up an old session.
        delay = 8 - (time.monotonic() - last_attempt)
        if delay > 0:
            await asyncio.sleep(delay)
        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            channel = await bot.fetch_channel(CHANNEL_ID)
        if not isinstance(channel, discord.VoiceChannel):
            log.error('VOICE_CHANNEL_ID must point to a permanent standard voice channel: %s', CHANNEL_ID)
            return
        vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
        if vc and vc.is_connected():
            if vc.channel and vc.channel.id == CHANNEL_ID:
                return
            log.warning('Voice moved to another channel; moving back')
            last_attempt = time.monotonic()
            await asyncio.wait_for(vc.move_to(channel), timeout=30)
            return
        if vc:
            try:
                await asyncio.wait_for(vc.disconnect(force=True), timeout=15)
            except Exception as exc:
                log.warning('Old voice cleanup: %r', exc)
        last_attempt = time.monotonic()
        log.info('Connecting to voice channel %s (%s)', channel.name, CHANNEL_ID)
        await asyncio.wait_for(channel.connect(timeout=30, reconnect=True, self_deaf=True), timeout=50)
        log.info('Voice connected: %s', channel.name)

async def voice_supervisor():
    await bot.wait_until_ready()
    failures = 0
    while not bot.is_closed():
        try:
            await ensure_connected()
            failures = 0
        except asyncio.CancelledError:
            raise
        except Exception:
            failures += 1
            log.exception('Voice connection failed (attempt %s); retrying', failures)
        wait_seconds = min(60, 5 * 2 ** min(failures, 4)) if failures else 15
        try:
            await asyncio.wait_for(wake.wait(), timeout=wait_seconds)
        except asyncio.TimeoutError:
            pass
        wake.clear()

class RoomBot(commands.Bot):
    async def setup_hook(self):
        self.voice_supervisor_task = asyncio.create_task(voice_supervisor())

# Setup hook is invoked after login; only one supervisor is ever started.
bot.setup_hook = RoomBot.setup_hook.__get__(bot, commands.Bot)

@bot.event
async def on_ready():
    log.info('Logged in as %s; monitoring permanent voice channel %s', bot.user, CHANNEL_ID)
    wake.set()

@bot.event
async def on_voice_state_update(member, before, after):
    if bot.user and member.id == bot.user.id:
        if after.channel is None:
            log.warning('Voice disconnected; requesting reconnect')
            wake.set()
        elif after.channel.id != CHANNEL_ID:
            log.warning('Voice moved away from target channel; requesting return')
            wake.set()

bot.run(TOKEN, reconnect=True)

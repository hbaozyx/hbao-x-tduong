import asyncio
import logging
import os

import discord
from discord.ext import commands, tasks

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('room247')

TOKEN = os.getenv('DISCORD_TOKEN', '').strip()
CHANNEL_ID_RAW = os.getenv('VOICE_CHANNEL_ID', '').strip()
if not TOKEN:
    raise RuntimeError('Missing DISCORD_TOKEN in Railway Variables')
if not CHANNEL_ID_RAW.isdigit():
    raise RuntimeError('VOICE_CHANNEL_ID must be a numeric Discord voice channel ID')
CHANNEL_ID = int(CHANNEL_ID_RAW)

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
voice_lock = asyncio.Lock()
reconnect_requested = asyncio.Event()

async def ensure_connected():
    async with voice_lock:
        try:
            channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
            if not isinstance(channel, discord.VoiceChannel):
                log.error('Configured ID is not a standard voice channel: %s', CHANNEL_ID)
                return
            vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
            if vc and vc.is_connected() and vc.channel and vc.channel.id == CHANNEL_ID:
                return
            if vc and vc.is_connected():
                log.warning('Bot moved to %s; moving back', vc.channel)
                await vc.move_to(channel)
                return
            if vc:
                try:
                    await asyncio.wait_for(vc.disconnect(force=True), timeout=12)
                except Exception as exc:
                    log.warning('Cleanup old voice client: %r', exc)
            log.info('Connecting to voice channel %s (%s)', channel.name, CHANNEL_ID)
            await channel.connect(timeout=25, reconnect=True, self_deaf=True)
            log.info('Connected to voice channel: %s (%s)', channel.name, CHANNEL_ID)
        except Exception:
            log.exception('Voice check failed; will retry')

@tasks.loop(seconds=15)
async def voice_watchdog():
    await ensure_connected()

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
    if bot.user and member.id == bot.user.id and after.channel is None:
        log.warning('Bot was disconnected from voice (previous channel: %s)', before.channel)
        # Let discord.py finish updating voice state before reconnecting.
        asyncio.create_task(reconnect_after_disconnect())

async def reconnect_after_disconnect():
    await asyncio.sleep(3)
    await ensure_connected()

bot.run(TOKEN, reconnect=True)

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

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

@tasks.loop(seconds=30)
async def ensure_voice():
    try:
        channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
        if not isinstance(channel, discord.VoiceChannel):
            log.error('VOICE_CHANNEL_ID is not a standard voice channel')
            return
        vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
        if vc and vc.is_connected():
            if vc.channel.id != CHANNEL_ID:
                await vc.move_to(channel)
            return
        if vc:
            await vc.disconnect(force=True)
        await channel.connect(timeout=30, reconnect=True, self_deaf=True)
        log.info('Connected to voice channel: %s (%s)', channel.name, CHANNEL_ID)
    except (discord.DiscordException, asyncio.TimeoutError, OSError) as exc:
        log.warning('Voice connection failed; retrying in 30s: %s', exc)

@ensure_voice.before_loop
async def before_voice():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    log.info('Logged in as %s', bot.user)
    if not ensure_voice.is_running():
        ensure_voice.start()

bot.run(TOKEN, reconnect=True)

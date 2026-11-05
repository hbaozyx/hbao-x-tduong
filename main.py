import os
import asyncio
import logging
import discord
from discord.ext import commands, tasks

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['VOICE_CHANNEL_ID'])

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

async def ensure_voice():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(CHANNEL_ID)
    if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
        logging.error('VOICE_CHANNEL_ID must point to a voice or stage channel')
        return
    vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
    try:
        if vc and vc.is_connected():
            if vc.channel.id != CHANNEL_ID:
                await vc.move_to(channel)
        else:
            if vc:
                await vc.disconnect(force=True)
            await channel.connect(self_deaf=True, reconnect=True, timeout=30)
        logging.info('Voice connected to %s', channel.name)
    except (discord.DiscordException, asyncio.TimeoutError, OSError):
        logging.exception('Voice connection failed; will retry')

@tasks.loop(seconds=45)
async def voice_watchdog():
    await ensure_voice()

@voice_watchdog.before_loop
async def before_watchdog():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    logging.info('Logged in as %s', bot.user)
    if not voice_watchdog.is_running():
        voice_watchdog.start()

bot.run(TOKEN, reconnect=True)

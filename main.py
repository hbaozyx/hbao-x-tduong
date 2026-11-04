import asyncio
import logging
import os

import discord
from discord.ext import commands, tasks

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('voice247')
TOKEN = os.environ['DISCORD_TOKEN'].strip()
CHANNEL_ID = int(os.environ['VOICE_CHANNEL_ID'])

class VoiceBot(commands.Bot):
    async def setup_hook(self):
        self.voice_lock = asyncio.Lock()
        self.voice_watchdog.start()

    @tasks.loop(seconds=45, reconnect=True)
    async def voice_watchdog(self):
        async with self.voice_lock:
            channel = self.get_channel(CHANNEL_ID)
            if channel is None:
                channel = await self.fetch_channel(CHANNEL_ID)
            if not isinstance(channel, discord.VoiceChannel):
                log.error('VOICE_CHANNEL_ID is not a permanent VoiceChannel: %s', CHANNEL_ID)
                return
            vc = discord.utils.get(self.voice_clients, guild=channel.guild)
            if vc is not None and vc.is_connected():
                if vc.channel and vc.channel.id == CHANNEL_ID:
                    return
                log.warning('VOICE_MOVED: moving back to %s', CHANNEL_ID)
                await asyncio.wait_for(vc.move_to(channel), timeout=30)
                return
            if vc is not None:
                log.warning('VOICE_STALE: clearing disconnected voice client')
                try:
                    await asyncio.wait_for(vc.disconnect(force=True), timeout=15)
                except Exception:
                    log.exception('VOICE_CLEANUP_ERROR')
            log.info('VOICE_JOIN_ATTEMPT channel=%s', CHANNEL_ID)
            # Match the working bot: let discord.py attempt voice reconnects.
            connected = await asyncio.wait_for(
                channel.connect(self_deaf=True, reconnect=True, timeout=30),
                timeout=70,
            )
            log.info('VOICE_CONNECTED channel=%s connected=%s', CHANNEL_ID, connected.is_connected())

    @voice_watchdog.before_loop
    async def before_voice_watchdog(self):
        await self.wait_until_ready()

    @voice_watchdog.error
    async def voice_watchdog_error(self, error):
        log.exception('VOICE_WATCHDOG_STOPPED: %r', error)

intents = discord.Intents.default()
bot = VoiceBot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    log.info('GATEWAY_READY user=%s discord.py=%s', bot.user, discord.__version__)

@bot.event
async def on_voice_state_update(member, before, after):
    if bot.user and member.id == bot.user.id:
        log.info('BOT_VOICE_STATE before=%s after=%s',
                 getattr(before.channel, 'id', None),
                 getattr(after.channel, 'id', None))

bot.run(TOKEN, reconnect=True)

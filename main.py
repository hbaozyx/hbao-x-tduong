import asyncio
import logging
import os
import time

import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('room247')
TOKEN = os.environ['DISCORD_TOKEN'].strip()
CHANNEL_ID = int(os.environ['VOICE_CHANNEL_ID'])

class RoomBot(commands.Bot):
    async def setup_hook(self):
        self.voice_lock = asyncio.Lock()
        self.voice_wake = asyncio.Event()
        self.supervisor = asyncio.create_task(self.voice_supervisor())

    async def voice_supervisor(self):
        await self.wait_until_ready()
        failures = 0
        while not self.is_closed():
            try:
                async with self.voice_lock:
                    channel = self.get_channel(CHANNEL_ID) or await self.fetch_channel(CHANNEL_ID)
                    if not isinstance(channel, discord.VoiceChannel):
                        raise ValueError('VOICE_CHANNEL_ID must identify a permanent voice channel')
                    vc = discord.utils.get(self.voice_clients, guild=channel.guild)
                    if vc and vc.is_connected():
                        if vc.channel and vc.channel.id != CHANNEL_ID:
                            await asyncio.wait_for(vc.move_to(channel), timeout=30)
                        failures = 0
                    else:
                        if vc:
                            try:
                                await asyncio.wait_for(vc.disconnect(force=True), timeout=15)
                            except Exception:
                                log.exception('Old voice session cleanup failed')
                        # Allow Discord to retire the previous voice session before joining again.
                        await asyncio.sleep(5)
                        log.info('Creating fresh voice session for %s', CHANNEL_ID)
                        # Do not let discord.py internally retry an invalid voice session forever.
                        vc = await channel.connect(timeout=30, reconnect=False, self_deaf=True)
                        log.info('Voice connected to %s (connected=%s)', channel.name, vc.is_connected())
                        failures = 0
            except asyncio.CancelledError:
                raise
            except Exception:
                failures += 1
                log.exception('Voice supervisor failure #%d', failures)
            delay = min(120, 5 * (2 ** min(failures, 5))) if failures else 15
            try:
                await asyncio.wait_for(self.voice_wake.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            self.voice_wake.clear()
            if failures:
                await asyncio.sleep(min(30, 3 * failures))

intents = discord.Intents.default()
bot = RoomBot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    log.info('Gateway ready: %s; discord.py %s', bot.user, discord.__version__)
    bot.voice_wake.set()

@bot.event
async def on_voice_state_update(member, before, after):
    if bot.user and member.id == bot.user.id:
        if after.channel is None:
            log.warning('Voice state says bot left channel; scheduling fresh join')
            bot.voice_wake.set()
        elif after.channel.id != CHANNEL_ID:
            log.warning('Bot moved to another voice channel; scheduling return')
            bot.voice_wake.set()

bot.run(TOKEN, reconnect=True)

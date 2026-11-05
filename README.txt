TDUONG VOICE 24/7 - RAILWAY

1. Upload main.py and requirements.txt to Tduong GitHub repository.
2. Railway > Tduong service > Variables:
   DISCORD_TOKEN = Tduong bot token
   VOICE_CHANNEL_ID = target voice channel ID
3. Start Command: python main.py
4. Deploy, then check logs for GATEWAY_READY and VOICE_CONNECTED.
5. Keep Kem service and its variables unchanged.

This bot automatically retries while the Railway process is running.
It cannot prevent platform sleeping, Discord voice outages, channel deletion,
or being kicked by another bot. If a temporary room is deleted, use a permanent channel.
Do not run two instances of the same Discord bot token simultaneously.

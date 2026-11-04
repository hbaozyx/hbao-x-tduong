# Railway Voice watchdog
Replace main.py, requirements.txt, Dockerfile in your GitHub repository.
Keep Railway Variables: DISCORD_TOKEN and VOICE_CHANNEL_ID.
Keep one Railway replica, no cron. Do not run a second process using the same token.
Watch logs for VOICE_JOIN_ATTEMPT, VOICE_CONNECTED, VOICE_STALE and BOT_VOICE_STATE.
The bot retries on a 45-second watchdog cycle and uses discord.py reconnect=True.
This improves recovery but cannot guarantee uninterrupted Discord Voice connectivity.

Discord Voice Keeper - Railway

1. Upload main.py and requirements.txt to the root of your GitHub repository.
2. Railway Variables:
   DISCORD_TOKEN = your Discord bot token
   VOICE_CHANNEL_ID = the target voice channel ID
3. Railway start command: python main.py
4. Deploy and check Deploy Logs for 'Voice connected'.

The watchdog checks every 15 seconds, but retries with backoff on connection failures.
If the log repeatedly says 'Starting voice handshake' then TimeoutError, investigate Railway-to-Discord voice connectivity and channel permissions; code cannot guarantee a working voice route.
This does not create a 24/7 uptime guarantee if the hosting service stops the deployment.

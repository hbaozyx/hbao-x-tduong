# Railway Discord Voice 24/7

This project keeps a bot in a **permanent** Discord voice channel. It does not require your PC or phone to stay online.

## Railway
1. Replace `main.py`, `requirements.txt`, and `Dockerfile` in the GitHub repo connected to Railway.
2. Set environment variables on Railway: `DISCORD_TOKEN` (secret bot token), `VOICE_CHANNEL_ID` (permanent voice channel ID).
3. Start Command: `python main.py` (or let Dockerfile CMD run it).
4. Keep 1 replica, no cron, disable App Sleeping/Serverless if enabled.
5. Deploy and watch logs for `VOICE_CONNECTED`, `BOT_VOICE_STATE`, `Voice unhealthy`, `VOICE_SUPERVISOR_ERROR`.
6. Test with the voice room empty for 15 minutes, then 1 hour and 24 hours.

Do not upload a token into GitHub or send it to anyone. Only one running process/service should use the same bot token. The code cannot guarantee 100% uptime against Discord or Railway outages; it attempts automatic recovery.

If the bot keeps dropping, capture full logs and check Discord channel Connect/View Channel permissions, RTC Region, and whether another app is logged in with the same bot token.

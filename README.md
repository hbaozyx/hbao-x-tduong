# Discord Room 24/7

A Discord bot that stays in one standard voice channel even when empty.

## Deploy to Railway
1. Upload main.py, requirements.txt, Dockerfile, .env.example and .gitignore to a private GitHub repository (at its root).
2. Railway > New Project > Deploy from GitHub repo > select repository.
3. In service Variables set `DISCORD_TOKEN` to your **bot** token and `VOICE_CHANNEL_ID` to your voice channel ID.
4. Deploy staged changes. Ensure only one replica is running.
5. Check deployment logs for `Connected to voice channel`.

The bot requires View Channel and Connect permissions. It does not need Message Content intent. It does not transmit audio. It does not require a public domain or HTTP server.

It reconnects on recoverable network failures, but cannot guarantee 100% uptime if Railway is stopped or Discord voice is unavailable.

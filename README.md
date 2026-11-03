# Discord Room 24/7

Bot stays connected to one standard Discord voice channel even when empty. It checks every 15 seconds and retries after a bot voice disconnect event. Discord/network/hosting outages may still interrupt it.

## Deploy to Railway

1. Upload `main.py`, `requirements.txt`, `Dockerfile`, `.gitignore`, and `.env.example` to a GitHub repository root.
2. Railway → New Project → Deploy from GitHub repo.
3. Add service variables `DISCORD_TOKEN` (bot token) and `VOICE_CHANNEL_ID` (numeric channel ID).
4. Deploy; keep one replica and inspect Deploy Logs for `Connected to voice channel`.
5. Give the bot `View Channel` and `Connect` permissions in the voice channel.

**Never put the real token into GitHub.** If a token was exposed, reset it in Discord Developer Portal and update Railway Variables.

If the bot disconnects only when the last person leaves, check Discord Audit Log for manual/moderation disconnections and any other bot's automatic voice controls. The watchdog cannot override missing permissions or an external service repeatedly disconnecting it.

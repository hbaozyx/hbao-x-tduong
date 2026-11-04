Replace main.py and requirements.txt in GitHub repository.
Railway Variables: DISCORD_TOKEN and VOICE_CHANNEL_ID.
Railway Start Command: python main.py.
Use one running deployment/replica per bot token.
Use a permanent standard voice channel with Connect/View Channel permissions.
This fix disables discord.py internal voice reconnect attempts and delegates new-session retries to a single supervisor. Discord/Railway outages can still interrupt voice.

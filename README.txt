Railway deployment:
1. Upload main.py and requirements.txt to your GitHub repo.
2. Set Railway Variables DISCORD_TOKEN and VOICE_CHANNEL_ID.
3. Set start command: python main.py
4. Use a permanent standard voice channel. Give bot View Channel, Connect permissions.
5. Keep only one service/replica connected with this token.
6. This supervisor reconnects after disconnections but cannot prevent Discord/Railway outages or forced kicks.

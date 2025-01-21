# Telegram File Rename Bot

This bot helps rename files in Telegram channels and groups by:
1. Removing usernames from the start of filenames
2. Removing extra text after the file extension (.mkv)
3. Adding a custom channel username at the end

## Setup Instructions

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram

3. Edit `rename_bot.py` and replace `YOUR_BOT_TOKEN` with your actual bot token

4. Run the bot:
```bash
python rename_bot.py
```

## Usage

1. Add the bot to your channel or group
2. Give it admin permissions to delete and send messages
3. Forward any message or file to the bot
4. The bot will automatically rename the file according to the specified format

## Example

Input:
```
[Tg-@New_Movies_OnTG] Azaad (2025) 720p PRE-HD [Hindi ORG-DD2.0] Full Movie x264 AAC.mkv

♻️ For Loot Deals Offers 🔥
📌 Join :- @Tg_Shoping
```

Output:
```
Azaad (2025) 720p PRE-HD [Hindi ORG-DD2.0] Full Movie x264 AAC.mkv

Join - @TGMoviez_Hub
```

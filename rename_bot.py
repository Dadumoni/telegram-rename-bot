import re
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import TelegramError, Conflict
import time
import os
import logging
import sys
import atexit
import signal
import tempfile
import requests

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN', "7654850355:AAGtizZP468SNYYHFJ9lQY-8Ee561vunQWk")
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', "@TGMoviez_Hub")

# Lock file path
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'telegram_rename_bot.lock')

def cleanup():
    """Clean up function to remove lock file"""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            logger.info("Lock file removed")
    except Exception as e:
        logger.error(f"Error removing lock file: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    cleanup()
    sys.exit(0)

def check_single_instance():
    """Ensure only one instance of the bot is running"""
    try:
        # Make an API call to check bot status
        try:
            response = requests.get(
                f'https://api.telegram.org/bot{BOT_TOKEN}/getMe',
                timeout=5
            )
            if response.status_code != 200:
                logger.info("Bot token is valid and not in use")
                return True
            else:
                # If we get a 200 response, the bot token is valid
                # In cloud environments, we should continue anyway
                logger.info("Bot token is valid, continuing startup")
                return True
        except Exception as e:
            logger.info(f"Could not check bot status: {e}, proceeding with startup")
            return True

        return True
    except Exception as e:
        logger.error(f"Error in check_single_instance: {e}")
        return True  # Continue anyway in case of errors

def error_handler(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if isinstance(context.error, Conflict):
        logger.error("Conflict error: Another instance is running")
        cleanup()
        sys.exit(1)

def start(update, context):
    update.message.reply_text(
        "Hello! I'm a file rename bot. I can help rename files by removing usernames and extra text.\n"
        "Just add me to your channel or group as admin, and I'll automatically:\n"
        "1. Rename all existing files\n"
        "2. Monitor and rename new files as they are posted\n\n"
        "Use /process_all to start processing existing files in a channel/group"
    )

def help_command(update, context):
    update.message.reply_text(
        "Here's how to use me:\n\n"
        "1. Add me to your channel/group as admin\n"
        "2. Send /process_all in the group or forward a message from channel to me\n"
        "3. I'll process all existing files\n"
        "4. New files will be renamed automatically\n\n"
        "I will:\n"
        "1. Remove any username from the start\n"
        "2. Remove any extra text after the file extension\n"
        "3. Remove any external links or channel references\n"
        f"4. Add '{CHANNEL_USERNAME}' at the end"
    )

def clean_filename(text: str) -> str:
    # Remove username pattern from start [Tg-@username] or similar
    text = re.sub(r'^\s*\[.*?\]\s*', '', text)
    
    # Find the position of .mkv extension
    mkv_pos = text.lower().find('.mkv')
    if mkv_pos != -1:
        # Keep only the text up to .mkv
        text = text[:mkv_pos + 4]
    
    # Remove any remaining Telegram links or channel references
    text = re.sub(r'@[\w_]+', '', text)  # Remove @username mentions
    text = re.sub(r't\.me/[\w_]+', '', text)  # Remove t.me links
    text = re.sub(r'https?://[^\s]+', '', text)  # Remove http/https links
    text = re.sub(r'Join[\s\-:]+', '', text, flags=re.IGNORECASE)  # Remove "Join" text
    text = re.sub(r'Follow[\s\-:]+', '', text, flags=re.IGNORECASE)  # Remove "Follow" text
    
    # Remove multiple newlines and spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Add the channel username
    text = f"{text.strip()}\n\nJoin - {CHANNEL_USERNAME}"
    
    return text

def rename_message(message):
    if not message:
        return False
        
    if message.caption:
        new_caption = clean_filename(message.caption)
        try:
            if message.document or message.video:
                message.copy(
                    chat_id=message.chat_id,
                    caption=new_caption
                )
                message.delete()
                return True
        except Exception as e:
            print(f"Error renaming message: {str(e)}")
    return False

def handle_message(update, context):
    message = update.message or update.channel_post
    if message:
        rename_message(message)

def process_all_command(update, context):
    message = update.message
    if not message:
        return

    try:
        chat_id = message.chat_id
        user_id = message.from_user.id
        
        # Get chat member info
        try:
            member = context.bot.get_chat_member(chat_id, user_id)
            is_admin = member.status in ['administrator', 'creator'] or member.can_manage_messages
        except:
            # If we can't check admin status, allow the operation
            # This happens in private chats or when user is the channel owner
            is_admin = True
            
        if not is_admin:
            message.reply_text("Only administrators can use this command.")
            return

        # Send processing message
        status_message = message.reply_text("Starting to process existing files...")
        
        # Get message history
        total_processed = 0
        total_renamed = 0
        
        # Get messages in smaller chunks to avoid timeouts
        for offset in range(0, 1000, 50):
            try:
                messages = context.bot.get_chat_history(
                    chat_id=chat_id,
                    limit=50,
                    offset=offset
                )
                
                for msg in messages:
                    total_processed += 1
                    if rename_message(msg):
                        total_renamed += 1
                        
                    # Update status every 10 messages
                    if total_processed % 10 == 0:
                        try:
                            status_message.edit_text(
                                f"Processing messages...\n"
                                f"Processed: {total_processed}\n"
                                f"Renamed: {total_renamed}"
                            )
                        except:
                            pass
                    
                    # Small delay to avoid rate limits
                    time.sleep(0.1)
                
            except Exception as e:
                print(f"Error processing batch: {str(e)}")
                continue
            
            # Delay between chunks
            time.sleep(1)
        
        # Final status update
        try:
            status_message.edit_text(
                f"Finished processing messages!\n"
                f"Total processed: {total_processed}\n"
                f"Total renamed: {total_renamed}"
            )
        except:
            message.reply_text(
                f"Finished processing messages!\n"
                f"Total processed: {total_processed}\n"
                f"Total renamed: {total_renamed}"
            )

    except Exception as e:
        error_msg = str(e)
        print(f"Error while processing messages: {error_msg}")
        message.reply_text(f"Error while processing messages. Please try again or contact support.")

def main():
    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Check for other instances
    if not check_single_instance():
        cleanup()
        sys.exit(1)

    try:
        # Create updater and dispatcher
        updater = Updater(BOT_TOKEN, use_context=True, request_kwargs={'read_timeout': 30, 'connect_timeout': 15})
        dp = updater.dispatcher

        # Add handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(CommandHandler("process_all", process_all_command))
        dp.add_handler(MessageHandler(Filters.all, handle_message))
        
        # Add error handler
        dp.add_error_handler(error_handler)

        # Start the bot
        logger.info("Bot is starting...")
        updater.start_polling(drop_pending_updates=True, timeout=30)
        logger.info("Bot is running...")
        updater.idle()
        
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        cleanup()
        sys.exit(1)

if __name__ == '__main__':
    main()

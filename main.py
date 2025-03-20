# main.py
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from db import get_user, create_user
from news import fetch_ai_news
from feedback import add_feedback_buttons, handle_feedback
from preferences import initialize_preferences
from config import TELEGRAM_TOKEN

def start_command(update, context):
    """Start the bot and initialize user preferences"""
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        # New user - create with default preferences
        preferences = initialize_preferences(user.id)
        create_user(user.id, user.first_name, preferences)
        update.message.reply_text(
            f"Welcome {user.first_name}! I'll send you AI funding news. Use /news to get started."
        )
    else:
        update.message.reply_text(
            f"Welcome back {user.first_name}! Use /news to get the latest AI funding updates."
        )

def news_command(update, context):
    """Fetch and send personalized news"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    update.message.reply_text("Fetching your personalized AI funding news...")
    
    # Get news filtered by user preferences
    news_items = fetch_ai_news(user.get("preferences"))
    
    if not news_items:
        update.message.reply_text("Sorry, I couldn't find any relevant news today.")
        return
    
    # Send each news item
    for item in news_items:
        update.message.reply_text(
            f"{item['title']}\n"
            f"Source: {item['source']}\n"
            f"URL: {item['url']}"
        )
    
    # Add feedback buttons
    add_feedback_buttons(update, context, news_items)

def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("news", news_command))
    dp.add_handler(CallbackQueryHandler(handle_feedback))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
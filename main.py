# main.py - Main Telegram bot file

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler, ContextTypes
)
import asyncio
import datetime
import pytz
from tzlocal import get_localzone_name

from config import TELEGRAM_TOKEN, NEWS_UPDATE_TIME
from db import get_or_create_user, update_user_service_choice
from news_service import fetch_ai_funding_news, generate_news_summary
from twitter_service import fetch_top_tweets, filter_tweets, generate_twitter_summary
from feedback_handler import process_feedback
from utils import generate_content_id, split_long_message


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
CHOOSING_SERVICE, PROVIDING_FEEDBACK_REASON = range(2)

# Callback data
CB_NEWS = 'cb_news'
CB_TWITTER = 'cb_twitter'
CB_LIKE = 'cb_like'
CB_DISLIKE = 'cb_dislike'
CB_FEEDBACK = 'cb_feedback'

# Global variables for callback processing
user_feedback = {}  # Store user feedback temporarily


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the bot and ask user to choose service"""
    user = update.effective_user
    
    # Get or create user in database
    db_user = get_or_create_user(
        user.id, 
        username=user.username, 
        first_name=user.first_name
    )
    
    logger.info(f"User {user.id} started the bot")
    
    # Create keyboard for service selection
    keyboard = [
        [
            InlineKeyboardButton("AI Funding News", callback_data=CB_NEWS),
            InlineKeyboardButton("Top Twitter Voice Summary", callback_data=CB_TWITTER)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send welcome message
    await update.message.reply_text(
        f"Hi {user.first_name}! Welcome to the AI News Bot.\n\n"
        f"Please choose which type of updates you'd like to receive:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_SERVICE

async def handle_service_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle service choice callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    choice = query.data
    
    # Determine which service was chosen
    if choice == CB_NEWS:
        service_type = 'news'
        service_name = 'AI Funding News'
    elif choice == CB_TWITTER:
        service_type = 'twitter'
        service_name = 'Twitter Top Voices Summary'
    else:
        # Invalid choice
        await query.edit_message_text("Sorry, I didn't understand your choice. Please try again.")
        return ConversationHandler.END
    
    # Update user preference in the database
    update_user_service_choice(user_id, service_type)
    
    logger.info(f"User {user_id} chose {service_name}")
    
    # Inform the user about their choice
    await query.edit_message_text(
        f"Thanks for choosing {service_name}!\n\n"
        f"You will receive daily updates at {NEWS_UPDATE_TIME}.\n\n"
        f"If you want to get news right now, just once, send the command: /news"
    )
    
    return ConversationHandler.END

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide news on demand"""
    user_id = update.effective_user.id
    
    # Get or create user in database
    db_user = get_or_create_user(user_id)
    
    # Get service preference (default to news if not set)
    service_type = db_user.get('preferences', {}).get('service_type', 'news')
    
    await update.message.reply_text("Fetching your personalized summary... This might take a minute.")
    
    # Generate the appropriate summary based on service type
    if service_type == 'news':
        # Fetch AI funding news
        news_items = fetch_ai_funding_news()
        
        if not news_items:
            await update.message.reply_text("Sorry, I couldn't find any relevant AI funding news today.")
            return
        
        # Generate summary
        summary = generate_news_summary(user_id, news_items)
        content_id = generate_content_id(news_items)
        
    else:  # Twitter
        # Fetch tweets from top voices
        tweets = fetch_top_tweets()
        
        # Filter tweets based on user preferences
        excluded_accounts = db_user.get('preferences', {}).get('excluded_twitter_accounts', [])
        filtered_tweets = filter_tweets(tweets, excluded_accounts)
        
        if not filtered_tweets:
            await update.message.reply_text("Sorry, I couldn't find any relevant tweets from top AI voices today.")
            return
        
        # Generate summary
        summary = generate_twitter_summary(user_id, filtered_tweets)
        content_id = generate_content_id(filtered_tweets)
    
    # Split the message if it's too long
    message_parts = split_long_message(summary)
    
    # Send all parts except the last one
    for part in message_parts[:-1]:
        await update.message.reply_text(part)
    
    # For the last part, add feedback buttons
    keyboard = [
        [
            InlineKeyboardButton("👍 Liked it", callback_data=f"{CB_LIKE}_{content_id}"),
            InlineKeyboardButton("👎 Didn't like it", callback_data=f"{CB_DISLIKE}_{content_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the last part with feedback buttons
    await update.message.reply_text(
        message_parts[-1], 
        reply_markup=reply_markup
    )

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle feedback callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    # Parse callback data
    parts = callback_data.split('_')
    action = parts[0]
    content_id = parts[1] if len(parts) > 1 else None
    
    # Get user info
    db_user = get_or_create_user(user_id)
    service_type = db_user.get('preferences', {}).get('service_type', 'news')
    
    if action == CB_LIKE:
        # Process positive feedback
        response = process_feedback(user_id, service_type, content_id, 'positive')
        await query.edit_message_text(response)
        return ConversationHandler.END
        
    elif action == CB_DISLIKE:
        # Ask for reason for negative feedback
        keyboard = [
            [InlineKeyboardButton("Provide feedback", callback_data=f"{CB_FEEDBACK}_{content_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "I'm sorry you didn't find this useful. Would you like to tell me why?", 
            reply_markup=reply_markup
        )
        return CHOOSING_SERVICE  # Return to a valid state instead of ending the conversation
        
    elif action == CB_FEEDBACK:
        # Store content ID for this user
        user_feedback[user_id] = {
            'content_id': content_id,
            'service_type': service_type
        }
        
        await query.edit_message_text(
            "Please tell me what you didn't like about this summary, or what you'd prefer to see instead."
        )
        return PROVIDING_FEEDBACK_REASON
    
    return ConversationHandler.END

async def process_feedback_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the feedback reason provided by the user"""
    user_id = update.effective_user.id
    feedback_reason = update.message.text
    
    # Get stored feedback data
    feedback_data = user_feedback.get(user_id, {})
    content_id = feedback_data.get('content_id')
    service_type = feedback_data.get('service_type', 'news')
    
    if not content_id:
        await update.message.reply_text("Sorry, I couldn't process your feedback. Please try again later.")
        return ConversationHandler.END
    
    # Process the feedback
    response = process_feedback(user_id, service_type, content_id, 'negative', feedback_reason)
    
    # Clean up stored data
    if user_id in user_feedback:
        del user_feedback[user_id]
    
    await update.message.reply_text(response)
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display help information"""
    help_text = (
        "🤖 *AI News Bot Help* 🤖\n\n"
        "*Available Commands:*\n"
        "/start - Initialize the bot and choose which type of updates to receive\n"
        "/news - Get the latest personalized summary\n"
        "/help - Show this help message\n\n"
        "The bot will deliver daily updates at 10 PM based on your preferences.\n"
        "After each update, you can provide feedback to help improve future summaries."
    )
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def send_scheduled_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send scheduled updates to all users"""
    logger.info("Sending scheduled updates")
    
    # In a real implementation, you would:
    # 1. Query the database for all active users
    # 2. Check their service preference
    # 3. Generate and send appropriate updates
    
    # For this prototype, we'll use a placeholder
    logger.info("Scheduled updates would be sent here")
    
    # Note: This requires implementing a separate function to get all users
    # and their preferences from the database, then sending messages to each

def main() -> None:
    """Start the bot"""
    # Create the Application WITHOUT a job queue
    application = Application.builder().token(TELEGRAM_TOKEN).job_queue(None).build()

    # application.job_queue.run_daily(
    #     send_scheduled_updates,
    #     time=datetime.time(hour=int(NEWS_UPDATE_TIME.split(':')[0]), 
    #                     minute=int(NEWS_UPDATE_TIME.split(':')[1])),
    #     days=(0, 1, 2, 3, 4, 5, 6)
    # )
    
    # Conversation handler for the initial service choice
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CallbackQueryHandler(handle_feedback, pattern=f"^({CB_LIKE}|{CB_DISLIKE}|{CB_FEEDBACK})_.*$")
        ],
        states={
            CHOOSING_SERVICE: [
                CallbackQueryHandler(handle_service_choice, pattern=f"^({CB_NEWS}|{CB_TWITTER})$"),
                CallbackQueryHandler(handle_feedback, pattern=f"^({CB_LIKE}|{CB_DISLIKE}|{CB_FEEDBACK})_.*$")
            ],
            PROVIDING_FEEDBACK_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_feedback_reason)
            ]
        },
        fallbacks=[CommandHandler("help", help_command)]
    )
    
    # Register handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot started")

if __name__ == '__main__':
    main()
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    ConversationHandler, CallbackContext
)
import logging
from config import TELEGRAM_TOKEN
from db import get_user, create_user, update_user_preferences
from news import fetch_ai_tech_news
from content import generate_social_post

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
CHOOSING_INTEREST, SELECT_NEWS, CHOOSING_PLATFORM = range(3)

def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask for preferences."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Check if user exists in database
    user_data = get_user(user_id)
    
    if not user_data:
        # Create new user with default preferences
        create_user(user_id, user.first_name)
        
        # Ask for interests
        reply_keyboard = [['General AI', 'AI Research'], 
                           ['AI Products', 'AI Business']]
        
        update.message.reply_text(
            f"Hi {user.first_name}! I'll help you create social media posts about AI news.\n\n"
            "What specific AI topics interest you most?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSING_INTEREST
    else:
        # Welcome back existing user
        update.message.reply_text(
            f"Welcome back {user.first_name}! Type /news to get today's AI news and create posts.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

def save_interest(update: Update, context: CallbackContext) -> int:
    """Save the selected interest to the database."""
    user_id = str(update.effective_user.id)
    text = update.message.text.lower()
    
    # Map the text input to interest categories
    interest_map = {
        'general ai': 'general',
        'ai research': 'research',
        'ai products': 'products',
        'ai business': 'business'
    }
    
    interest = interest_map.get(text, 'general')
    
    # Get current user data
    user_data = get_user(user_id)
    preferences = user_data.get('preferences', {"platforms": ["twitter"]})
    
    # Update preferences
    preferences['interest'] = interest
    update_user_preferences(user_id, preferences)
    
    update.message.reply_text(
        f"Great! I'll focus on {interest} AI news. Type /news whenever you want the latest updates.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def news_command(update: Update, context: CallbackContext) -> int:
    """Get the latest AI news and display them."""
    user_id = str(update.effective_user.id)
    
    # Get user data
    user_data = get_user(user_id)
    if not user_data:
        update.message.reply_text("Please use /start to set up your preferences first.")
        return ConversationHandler.END
    
    # Fetch news
    update.message.reply_text("Fetching the latest AI news... Give me a moment.")
    news_items = fetch_ai_tech_news()
    
    if not news_items:
        update.message.reply_text("I couldn't find any relevant AI news right now. Please try again later.")
        return ConversationHandler.END
    
    # Send news summary
    update.message.reply_text("Here's today's AI news summary:")
    
    for i, item in enumerate(news_items, 1):
        update.message.reply_text(f"{i}. {item['title']}\nSource: {item['source']}\nURL: {item['url']}")
    
    # Store news items in context
    context.user_data['news_items'] = news_items
    
    # Ask which news to create post for
    reply_keyboard = [[str(i)] for i in range(1, len(news_items) + 1)]
    update.message.reply_text(
        "Reply with the number of the news item you'd like to create a post for:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return SELECT_NEWS

def select_news(update: Update, context: CallbackContext) -> int:
    """Handle the news selection and ask for platform."""
    try:
        selection = int(update.message.text) - 1
        news_items = context.user_data.get('news_items', [])
        
        if 0 <= selection < len(news_items):
            # Store selected news
            context.user_data['selected_news'] = news_items[selection]
            
            # Ask for platform
            reply_keyboard = [['Twitter'], ['LinkedIn'], ['Reddit']]
            update.message.reply_text(
                "Which platform would you like to create content for?",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            )
            return CHOOSING_PLATFORM
        else:
            update.message.reply_text("Invalid selection. Please try again.")
            return SELECT_NEWS
    except (ValueError, IndexError):
        update.message.reply_text("Please enter a valid number.")
        return SELECT_NEWS

def generate_post(update: Update, context: CallbackContext) -> int:
    """Generate and display the social media post."""
    user_id = str(update.effective_user.id)
    platform = update.message.text.lower()
    
    # Get user preferences
    user_data = get_user(user_id)
    user_interest = user_data.get('preferences', {}).get('interest', 'general')
    
    # Get selected news
    selected_news = context.user_data.get('selected_news')
    if not selected_news:
        update.message.reply_text("Something went wrong. Please try again.")
        return ConversationHandler.END
    
    # Generate post
    update.message.reply_text("Creating your social media post...")
    post = generate_social_post(selected_news, platform, user_interest)
    
    # Show generated post
    update.message.reply_text(
        f"Here's your {platform} post:\n\n{post}\n\n"
        f"Link: {selected_news['url']}",
        reply_markup=ReplyKeyboardRemove()
    )
    
    update.message.reply_text(
        "Copy this text to post it on your social media. In the future, I'll be able to post directly for you!"
    )
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel and end the conversation."""
    update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token
    updater = Updater(TELEGRAM_TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Add conversation handler for onboarding
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_INTEREST: [MessageHandler(Filters.text & ~Filters.command, save_interest)],
            SELECT_NEWS: [MessageHandler(Filters.text & ~Filters.command, select_news)],
            CHOOSING_PLATFORM: [MessageHandler(Filters.text & ~Filters.command, generate_post)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    dispatcher.add_handler(conv_handler)
    
    # Add news command handler
    dispatcher.add_handler(CommandHandler('news', news_command))
    
    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
# /main.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    ConversationHandler, CallbackContext
)
import logging
from config import TELEGRAM_TOKEN
from db import get_user, create_user, update_user_preferences, create_user_tag
from news import fetch_ai_tech_news
from ai_analysis import extract_interests_with_ai

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
GATHERING_INTERESTS, CHOOSING_INTEREST = range(2)

def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask for preferences."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Check if user exists in database
    user_data = get_user(user_id)
    
    if not user_data:
        # Create new user with default preferences
        create_user(user_id, user.first_name)
        
        # Ask for interests - offer AI Funding News or Custom
        reply_keyboard = [['AI Funding News'], ['Custom Preferences']]
        
        update.message.reply_text(
            f"Hi {user.first_name}! I'll help you stay updated on AI funding news.\n\n"
            "Choose from our standard AI Funding News or set custom preferences.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSING_INTEREST
    else:
        # Welcome back existing user
        update.message.reply_text(
            f"Welcome back {user.first_name}! Type /news to get today's AI funding news.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

def process_interests(update: Update, context: CallbackContext) -> int:
    """Process the user's open-ended response with AI."""
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    
    # Let the user know we're processing
    update.message.reply_text("Analyzing your interests... One moment please.")
    
    # Extract preferences using AI
    preferences = extract_interests_with_ai(user_text)
    
    # Update user preferences in database
    update_user_preferences(user_id, preferences)
    
    # Create tags for this user
    for topic, weight in preferences["interests"].items():
        create_user_tag(user_id, topic, weight)
    
    # Confirm and provide next steps
    topics_list = list(preferences["interests"].keys())
    topic_text = ", ".join(topics_list[:3])
    if len(topics_list) > 3:
        topic_text += f", and {len(topics_list)-3} more"
        
    update.message.reply_text(
        f"Thanks! I'll focus on bringing you news about {topic_text}.\n\n"
        f"I've identified your primary interest as a {preferences['role']} in the AI space.\n\n"
        "Type /news anytime to get personalized AI updates.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def save_interest(update: Update, context: CallbackContext) -> int:
    """Save the selected interest category to the database."""
    user_id = str(update.effective_user.id)
    selected_option = update.message.text
    
    if selected_option == 'Custom Preferences':
        update.message.reply_text(
            "Great! Please tell me more about your interests in AI funding and investment.\n\n"
            "For example, you might say: \"I'm a VC interested in early-stage AI startups, "
            "especially in healthcare, NLP, and computer vision. I prefer detailed technical news.\""
        )
        return GATHERING_INTERESTS
    
    # For 'AI Funding News' option
    preferences = {
        "role": "investor",
        "news_focus": "funding",
        "interests": {
            "ai_funding": 1.0,
            "venture capital": 0.9,
            "startups": 0.8
        },
        "technical_level": "intermediate",
        "recency_preference": 2  # Default to last 2 days
    }
    
    # Update user preferences in database
    update_user_preferences(user_id, preferences)
    
    # Create a single tag for this user
    create_user_tag(user_id, "ai_funding", 1.0)
    
    # Provide confirmation
    update.message.reply_text(
        "Great! I'll focus on finding AI funding news for you.\n\n"
        "This includes investments, fundraising rounds, and venture capital activity in the AI space.\n\n"
        "Type /news anytime to get the latest AI funding updates.",
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
    
    # Fetch news based on user preferences
    update.message.reply_text("Fetching the latest AI funding news tailored to your interests... Give me a moment.")
    
    news_items = fetch_ai_tech_news(user_data.get('preferences'))
    
    if not news_items:
        update.message.reply_text("I couldn't find any relevant AI funding news right now. Please try again later.")
        return ConversationHandler.END
    
    # Send news summary - now with relevance explanations if available
    update.message.reply_text("Here's today's AI funding news customized for your interests:")
    
    for i, item in enumerate(news_items, 1):
        news_message = f"{i}. {item['title']}\n"
        news_message += f"Source: {item['source']}\n"
        news_message += f"Date: {item['date']}\n"
        news_message += f"URL: {item['url']}\n"
        
        # Add AI explanations if available
        if 'ai_explanation' in item:
            news_message += f"\nWhy it matters: {item['ai_explanation']}\n"
        
        # Add the AI relevance score if available
        if 'ai_relevance_score' in item:
            news_message += f"Relevance Score: {item['ai_relevance_score']}/10\n"
            
        update.message.reply_text(news_message)
    
    # Provide a friendly closing message
    update.message.reply_text(
        "That's all for now! Check back later for more updates or use /reset to change your preferences."
    )
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel and end the conversation."""
    update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def reset_command(update: Update, context: CallbackContext) -> int:
    """Reset user preferences and start over."""
    user_id = str(update.effective_user.id)
    user = update.effective_user
    
    # Reset their preferences to empty/default
    update_user_preferences(user_id, {})
    
    # Clear all user tags to prevent duplicate key errors
    # delete_user_tags(user_id)  # Implement this function if needed
    
    # Offer AI Funding News or Custom
    reply_keyboard = [['AI Funding News'], ['Custom Preferences']]
    
    update.message.reply_text(
        f"Hi {user.first_name}! I've reset your preferences. Let's start over.\n\n"
        "Choose from our standard AI Funding News or set custom preferences.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CHOOSING_INTEREST

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text(
        "Here's how to use the AI Funding News Bot:\n\n"
        "/start - Begin or restart the bot\n"
        "/news - Get the latest AI funding news\n"
        "/reset - Reset your preferences\n"
        "/help - Show this help message\n"
        "/cancel - Cancel the current operation"
    )

def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token
    updater = Updater(TELEGRAM_TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Add conversation handler for onboarding and news flow
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('news', news_command),
            CommandHandler('reset', reset_command)
        ],
        states={
            CHOOSING_INTEREST: [MessageHandler(Filters.text & ~Filters.command, save_interest)],
            GATHERING_INTERESTS: [MessageHandler(Filters.text & ~Filters.command, process_interests)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    dispatcher.add_handler(conv_handler)
    
    # Add standalone command handlers
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
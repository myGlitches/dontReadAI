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
from content import generate_social_post
from ai_analysis import extract_interests_with_ai

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
GATHERING_INTERESTS, CHOOSING_INTEREST, SELECT_NEWS, CHOOSING_PLATFORM = range(4)

def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask for preferences."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Check if user exists in database
    user_data = get_user(user_id)
    
    if not user_data:
        # Create new user with default preferences
        create_user(user_id, user.first_name)
        
        # Ask open-ended question
        update.message.reply_text(
            f"Hi {user.first_name}! I'll help you create personalized social media posts about AI news.\n\n"
            "Tell me briefly about your interest in AI - what specific topics, technologies, or news would be most valuable to you?",
            reply_markup=ReplyKeyboardRemove()
        )
        return GATHERING_INTERESTS
    else:
        # Welcome back existing user
        update.message.reply_text(
            f"Welcome back {user.first_name}! Type /news to get today's AI news tailored to your interests.",
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
    
    # Fetch news based on user preferences
    update.message.reply_text("Fetching the latest AI news tailored to your interests... Give me a moment.")
    news_items = fetch_ai_tech_news(user_data.get('preferences'))
    
    if not news_items:
        update.message.reply_text("I couldn't find any relevant AI news right now. Please try again later.")
        return ConversationHandler.END
    
    # Send news summary
    update.message.reply_text("Here's today's AI news summary customized for you:")
    
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
    user_preferences = user_data.get('preferences', {})
    
    # Get selected news
    selected_news = context.user_data.get('selected_news')
    if not selected_news:
        update.message.reply_text("Something went wrong. Please try again.")
        return ConversationHandler.END
    
    # Generate post
    update.message.reply_text("Creating your personalized social media post...")
    post = generate_social_post(selected_news, platform, user_preferences)
    
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

def reset_command(update: Update, context: CallbackContext) -> int:
    """Reset user preferences and start over."""
    user_id = str(update.effective_user.id)
    user = update.effective_user
    
    # Delete user from database or reset their preferences
    # Option 1: If you have a delete_user function
    # delete_user(user_id)
    
    # Option 2: Or reset their preferences to empty/default
    update_user_preferences(user_id, {})
    
    update.message.reply_text(
        f"Hi {user.first_name}! I've reset your preferences. Let's start over.\n\n"
        "Tell me briefly about your interest in AI - what specific topics, technologies, or news would be most valuable to you?",
        reply_markup=ReplyKeyboardRemove()
    )
    return GATHERING_INTERESTS

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
            GATHERING_INTERESTS: [MessageHandler(Filters.text & ~Filters.command, process_interests)],
            CHOOSING_INTEREST: [MessageHandler(Filters.text & ~Filters.command, save_interest)],
            SELECT_NEWS: [MessageHandler(Filters.text & ~Filters.command, select_news)],
            CHOOSING_PLATFORM: [MessageHandler(Filters.text & ~Filters.command, generate_post)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    dispatcher.add_handler(conv_handler)
    
    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
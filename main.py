# main.py
from telegram import ReplyKeyboardMarkup  # Add this import
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
from db import get_user, create_user, update_user_preferences, create_user_tag, delete_user_tags
from news import fetch_ai_news
from feedback import add_feedback_buttons, handle_feedback
from preferences import initialize_preferences
from config import TELEGRAM_TOKEN
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

# Define conversation states
CHOOSING_INTEREST, GATHERING_INTERESTS = range(2)

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

def save_interest(update, context):
    """Save the selected interest category to the database."""
    user_id = str(update.effective_user.id)
    selected_option = update.message.text
    
    if selected_option == 'Custom Preferences':
        update.message.reply_text(
            "Great! Please tell me more about your interests in AI funding and investment.\n\n"
            "For example, you might say: \"I'm interested in early-stage AI startups, "
            "especially in healthcare, NLP, and computer vision. I prefer detailed technical news.\""
        )
        return GATHERING_INTERESTS
    
    preferences = {
        "interests": {
            "ai_funding": 1.0,
            "venture capital": 0.9,
            "startups": 0.8
        },
        "exclusions": [],
        "technical_level": "intermediate"
    }
    
    try:
        # Update user preferences in database
        update_user_preferences(user_id, preferences)
        
        try:
            # First clear existing tags - if function exists
            delete_user_tags(user_id)
        except Exception as e:
            print(f"Warning: Could not delete existing tags: {e}")
        
        # Create tags for this user
        for topic, weight in preferences["interests"].items():
            try:
                create_user_tag(user_id, topic, weight)
            except Exception as e:
                print(f"Warning: Could not create tag '{topic}': {e}")
    except Exception as e:
        print(f"Error updating preferences: {e}")
        update.message.reply_text(
            "Sorry, there was an error saving your preferences. Please try again."
        )
        return ConversationHandler.END
    
    # Provide confirmation
    update.message.reply_text(
        "Great! I'll focus on finding AI funding news for you.\n\n"
        "This includes investments, fundraising rounds, and venture capital activity in the AI space.\n\n"
        "Type /news anytime to get the latest AI funding updates.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def process_interests(update, context):
    """Process the user's custom interests and save them."""
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    
    # Let the user know we're processing
    update.message.reply_text("Analyzing your interests... One moment please.")
    
    # Here you'd normally use an AI model to extract interests
    # For simplicity, we'll just extract basic keywords
    interests = {}
    
    # Simple keyword extraction
    keywords = ["ai", "machine learning", "nlp", "computer vision", "healthcare", 
                "fintech", "startups", "funding", "series a", "early-stage"]
    
    for keyword in keywords:
        if keyword.lower() in user_text.lower():
            interests[keyword] = 0.8
    
    # If no keywords found, add some defaults
    if not interests:
        interests = {
            "ai_funding": 0.9,
            "startups": 0.8
        }
    
    # Create preferences object
    preferences = {
        "interests": interests,
        "exclusions": [],
        "technical_level": "intermediate" if "technical" in user_text.lower() else "beginner"
    }
    
    # Update user preferences
    update_user_preferences(user_id, preferences)
    
    # First clear existing tags
    delete_user_tags(user_id)
    
    # Create tags for this user
    for topic, weight in interests.items():
        create_user_tag(user_id, topic, weight)
    
    # Confirm and provide next steps
    topics = list(interests.keys())
    topic_text = ", ".join(topics[:3])
    if len(topics) > 3:
        topic_text += f", and {len(topics)-3} more"
        
    update.message.reply_text(
        f"Thanks! I'll focus on bringing you news about {topic_text}.\n\n"
        "Type /news anytime to get personalized AI news updates.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def cancel(update, context):
    """Cancel and end the conversation."""
    update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def reset_preferences(update, context):
    """Reset user preferences and restart the preference setup process"""
    user_id = str(update.effective_user.id)
    user = update.effective_user
    
    # Clear user preferences
    empty_preferences = {
        "interests": {},
        "exclusions": []
    }
    
    update_user_preferences(user_id, empty_preferences)
    
    # Clear all user tags
    delete_user_tags(user_id)
    
    # Offer choice again
    reply_keyboard = [['AI Funding News'], ['Custom Preferences']]
    
    update.message.reply_text(
        f"Hi {user.first_name}! I've reset your preferences. Let's start over.\n\n"
        "Choose from our standard AI Funding News or set custom preferences.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    
    return CHOOSING_INTEREST

def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher
    
    # Add conversation handler for preference setup
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start_command),
            CommandHandler('reset', reset_preferences)
        ],
        states={
            CHOOSING_INTEREST: [MessageHandler(Filters.text & ~Filters.command, save_interest)],
            GATHERING_INTERESTS: [MessageHandler(Filters.text & ~Filters.command, process_interests)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("news", news_command))
    dp.add_handler(CallbackQueryHandler(handle_feedback))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
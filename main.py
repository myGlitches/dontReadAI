# main.py
from telegram import ReplyKeyboardMarkup  # Add this import
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
from db import get_user, create_user, update_user_preferences, create_user_tag, delete_user_tags,  get_user_tags, update_tag_weight
from news import fetch_ai_news
from feedback import add_feedback_buttons, handle_feedback
from preferences import initialize_preferences
from config import TELEGRAM_TOKEN
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from ai_analysis import extract_interests_with_ai
from utils import help_command
import logging


# Define conversation states
CHOOSING_INTEREST, GATHERING_INTERESTS = range(2)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    # Get news filtered by user preferences and user history
    news_items = fetch_ai_news(user_id, user.get("preferences"))
    
    if not news_items:
        update.message.reply_text("Sorry, I couldn't find any new relevant news today. Try again later or reset your history with /clear_history")
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

def interests_command(update, context):
    """Show the user their current interest tags"""
    user_id = update.effective_user.id
    tags = get_user_tags(user_id)
    
    if not tags:
        update.message.reply_text("You haven't set any specific interests yet. Use /reset to set up your interests.")
        return
    
    # Sort tags by weight (descending)
    sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
    
    # Format the message
    message = "Your current interests (sorted by importance):\n\n"
    for tag, weight in sorted_tags:
        # Convert weight to stars (1.0 = 5 stars, 0 = 0 stars)
        stars = int(weight * 5)
        star_display = "★" * stars + "☆" * (5 - stars)
        message += f"{tag}: {star_display} ({weight:.1f})\n"
    
    update.message.reply_text(message)
    
    # Add buttons for managing interests
    keyboard = [
        [InlineKeyboardButton("Add New Interest", callback_data="add_interest")],
        [InlineKeyboardButton("Reset All Interests", callback_data="reset_interests")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Options:", reply_markup=reply_markup)

def add_tag_command(update, context):
    """Add a new interest tag"""
    user_id = update.effective_user.id
    
    # Check if there are arguments (tag and optional weight)
    if not context.args:
        update.message.reply_text(
            "Usage: /add_tag <tag> [weight]\n"
            "Example: /add_tag computer_vision 0.8"
        )
        return
    
    tag = context.args[0].lower()
    
    # Get weight if provided, otherwise default to 0.7
    weight = 0.7
    if len(context.args) > 1:
        try:
            weight = float(context.args[1])
            # Ensure weight is between 0 and 1
            weight = max(0.0, min(1.0, weight))
        except ValueError:
            update.message.reply_text("Weight must be a number between 0 and 1")
            return
    
    # Add the tag
    create_user_tag(user_id, tag, weight)
    
    update.message.reply_text(f"Added interest tag '{tag}' with weight {weight:.1f}")

def remove_tag_command(update, context):
    """Remove an interest tag"""
    user_id = update.effective_user.id
    
    # Check if there are arguments (tag)
    if not context.args:
        update.message.reply_text(
            "Usage: /remove_tag <tag>\n"
            "Example: /remove_tag blockchain"
        )
        return
    
    tag = context.args[0].lower()
    
    # Check if tag exists
    tags = get_user_tags(user_id)
    if tag not in tags:
        update.message.reply_text(f"Tag '{tag}' not found in your interests.")
        return
    
    # Get current preferences
    user = get_user(user_id)
    preferences = user.get('preferences', {}) if user else {}
    
    # Remove the tag from interests
    if 'interests' in preferences and tag in preferences['interests']:
        del preferences['interests'][tag]
        
        # Update preferences
        update_user_preferences(user_id, preferences)
        
        update.message.reply_text(f"Removed interest tag '{tag}'")
    else:
        update.message.reply_text("Something went wrong. Tag not found in preferences.")

def adjust_interest_command(update, context):
    """Allow users to adjust the weight of an interest tag"""
    user_id = update.effective_user.id
    
    # Check if there are arguments (tag and weight)
    if len(context.args) != 2:
        update.message.reply_text(
            "Usage: /adjust_interest <tag> <weight>\n"
            "Example: /adjust_interest nlp 0.9"
        )
        return
    
    tag = context.args[0].lower()
    try:
        weight = float(context.args[1])
        # Ensure weight is between 0 and 1
        weight = max(0.0, min(1.0, weight))
    except ValueError:
        update.message.reply_text("Weight must be a number between 0 and 1")
        return
    
    # Check if tag exists
    tags = get_user_tags(user_id)
    if tag not in tags:
        update.message.reply_text(f"Tag '{tag}' not found in your interests.")
        return
    
    # Update the tag weight
    update_tag_weight(user_id, tag, weight)
    
    update.message.reply_text(f"Updated weight for '{tag}' to {weight:.1f}")

def history_command(update, context):
    """Show the user their recently viewed news"""
    user_id = update.effective_user.id
    
    from db import get_user_history
    history = get_user_history(user_id)
    
    if not history:
        update.message.reply_text("You haven't viewed any news items yet.")
        return
    
    message = "Your recently viewed news:\n\n"
    for i, item in enumerate(history[:10], 1):
        viewed_date = item.get('viewed_at', '').split('T')[0]
        message += f"{i}. {item.get('title', 'Unknown')} ({viewed_date})\n"
    
    update.message.reply_text(message)
    
    # Add button to clear history
    keyboard = [[InlineKeyboardButton("Clear History", callback_data="clear_history")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Options:", reply_markup=reply_markup)

def clear_history_command(update, context):
    """Clear the user's news viewing history"""
    user_id = update.effective_user.id
    
    from db import clear_user_history
    clear_user_history(user_id)
    
    update.message.reply_text("Your news viewing history has been cleared. You'll start seeing all news again.")

def handle_interest_callbacks(update, context):
    """Process callbacks related to interests"""
    query = update.callback_query
    query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    if data == "add_interest":
        # Start a conversation to add a new interest
        query.edit_message_text("Please type the interest you want to add, for example 'computer vision'")
        # Set conversation state to wait for interest input
        context.user_data['waiting_for'] = 'interest_name'
        return
        
    elif data == "reset_interests":
        # Reset user interests
        reset_preferences(update, context)
        
    elif data == "clear_history":
        # Clear viewing history
        from db import clear_user_history
        clear_user_history(user_id)
        query.edit_message_text("Your news viewing history has been cleared.")

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
    """Process the user's custom interests and save them using AI analysis."""
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    
    # Let the user know we're processing
    update.message.reply_text("Analyzing your interests with AI... One moment please.")
    
    try:
        # Use the AI-based analysis from ai_analysis.py
        ai_preferences = extract_interests_with_ai(user_text)
        
        # Update user preferences
        update_user_preferences(user_id, ai_preferences)
        
        # Clear existing tags
        delete_user_tags(user_id)
        
        # Create tags for this user from the AI-extracted interests
        for topic, weight in ai_preferences.get('interests', {}).items():
            create_user_tag(user_id, topic, weight)
        
        # Format a nice response with the extracted interests
        interest_list = ", ".join(list(ai_preferences.get('interests', {}).keys())[:3])
        if len(ai_preferences.get('interests', {})) > 3:
            interest_list += f", and {len(ai_preferences.get('interests', {})) - 3} more"
        
        tech_level = ai_preferences.get('technical_level', 'intermediate')
        role = ai_preferences.get('role', 'investor')
        
        update.message.reply_text(
            f"Thanks! I've analyzed your interests.\n\n"
            f"It seems you're most interested in: {interest_list}.\n"
            f"I've identified your profile as: {role} with {tech_level} technical knowledge.\n\n"
            f"Type /news anytime to get personalized AI funding updates or /interests to see all your interests.",
            reply_markup=ReplyKeyboardRemove()
        )
        
    except Exception as e:
        logger.error(f"Error in AI interest processing: {str(e)}")
        # Fallback to simpler keyword extraction
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
    
    # Register command handlers first
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("news", news_command))
    dp.add_handler(CommandHandler("interests", interests_command))
    dp.add_handler(CommandHandler("add_tag", add_tag_command))
    dp.add_handler(CommandHandler("remove_tag", remove_tag_command))
    dp.add_handler(CommandHandler("adjust_interest", adjust_interest_command))
    dp.add_handler(CommandHandler("history", history_command))
    dp.add_handler(CommandHandler("clear_history", clear_history_command))
    
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
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('help', help_command),  # Allow help during conversations
            CommandHandler('news', news_command)   # Allow news during conversations
        ]
    )
    
    dp.add_handler(conv_handler)
    
    # Add callback query handlers
    dp.add_handler(CallbackQueryHandler(handle_interest_callbacks, pattern='^(add_interest|reset_interests|clear_history)$'))
    dp.add_handler(CallbackQueryHandler(handle_feedback, pattern='^(like_|dislike_|reason_)'))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
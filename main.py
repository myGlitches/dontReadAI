from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
from db import get_user, create_user, update_user_preferences, create_user_tag, delete_user_tags, get_user_tags, update_tag_weight
from news import fetch_ai_news, generate_news_digest_for_user
from feedback import add_feedback_buttons, handle_feedback
from preferences import initialize_preferences
from config import TELEGRAM_TOKEN
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
            f"Welcome {user.first_name}! I'll send you personalized AI funding news with insights tailored to your interests. Use /news to get started or /digest for a comprehensive summary."
        )
    else:
        update.message.reply_text(
            f"Welcome back {user.first_name}! Use /news to get the latest AI funding updates or /digest for a summary of recent developments."
        )

def news_command(update, context):
    """Fetch and send personalized news with summaries"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    update.message.reply_text("Analyzing AI funding news based on your interests... This might take a moment while I find the most relevant updates.")
    
    # Get news filtered by user preferences with summaries
    news_items = fetch_ai_news(user_id, user.get("preferences"), include_summaries=True)
    
    if not news_items:
        update.message.reply_text("Sorry, I couldn't find any new relevant news today. Try again later or reset your history with /clear_history")
        return
    
    # Send each news item with enhanced details
    for item in news_items:
        # Format relevance score with stars
        relevance_score = item.get('relevance_score', 5)
        stars = '★' * int(relevance_score / 2) + '☆' * (5 - int(relevance_score / 2))
        
        # Format topics as hashtags
        topics = item.get('topics', [])
        topics_text = ' '.join(['#' + topic.replace(' ', '_') for topic in topics]) if topics else ''
        
        # Prepare the summary
        summary = item.get('summary', '')
        if summary:
            summary = f"\n\n📝 *Summary*:\n{summary}"
        
        # Create the message text
        message_text = (
            f"*{item['title']}*\n\n"
            f"📰 Source: {item['source']}\n"
            f"📊 Relevance: {stars} ({relevance_score}/10)\n"
            f"{topics_text}\n"
            f"{summary}\n\n"
            f"🔗 [Read Full Article]({item['url']})"
        )
        
        try:
            # Try to send with markdown formatting
            update.message.reply_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        except Exception as e:
            # Fallback to plain text if markdown fails
            logger.error(f"Error sending formatted message: {str(e)}")
            plain_message = (
                f"{item['title']}\n\n"
                f"Source: {item['source']}\n"
                f"Relevance: {relevance_score}/10\n"
                f"Topics: {', '.join(topics) if topics else 'Not specified'}\n"
                f"\nSummary:\n{summary}\n\n"
                f"Read Full Article: {item['url']}"
            )
            update.message.reply_text(plain_message, disable_web_page_preview=True)
    
    # Add feedback buttons
    add_feedback_buttons(update, context, news_items)

def digest_command(update, context):
    """Generate and send a comprehensive news digest"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    update.message.reply_text("Generating your personalized AI funding news digest... This may take a moment.")
    
    # Generate the digest
    digest_result = generate_news_digest_for_user(user_id, user.get("preferences"))
    
    if digest_result:
        # Format the digest message
        message_text = (
            f"📋 *Your AI Funding News Digest*\n"
            f"📅 {digest_result['date']}\n"
            f"📊 Based on {digest_result['news_count']} recent articles\n\n"
            f"{digest_result['digest']}\n\n"
            f"_Use /news to see individual articles with more details._"
        )
        
        try:
            # Try to send with markdown formatting
            update.message.reply_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        except Exception as e:
            # Fallback to plain text if markdown fails
            logger.error(f"Error sending formatted digest: {str(e)}")
            update.message.reply_text(
                digest_result['digest'],
                disable_web_page_preview=True
            )
    else:
        update.message.reply_text("Sorry, I couldn't generate a news digest at this time. Please try again later.")

# Original functions from main.py would remain the same...
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
            f"Type /news for personalized updates with summaries\n"
            f"Type /digest for a comprehensive news overview\n"
            f"Type /interests to see all your interests.",
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
            "Type /news to get personalized news updates.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return ConversationHandler.END

# Include other functions from main.py here...

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
    
    # Register command handlers
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("news", news_command))
    dp.add_handler(CommandHandler("digest", digest_command))  # New command for digests
    dp.add_handler(CommandHandler("interests", interests_command))
    dp.add_handler(CommandHandler("reset", reset_preferences))
    
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
            CommandHandler('help', help_command),
            CommandHandler('news', news_command)
        ]
    )
    
    dp.add_handler(conv_handler)
    
    # Add callback query handlers
    dp.add_handler(CallbackQueryHandler(handle_interest_callbacks, pattern='^(add_interest|reset_interests|clear_history)$'))
    dp.add_handler(CallbackQueryHandler(handle_feedback, pattern='^(like_|dislike_|reason_)'))
    
    # Include all other functions and handlers from main.py
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
# /feedback.py
import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import CallbackContext, CallbackQueryHandler, ConversationHandler, CommandHandler, MessageHandler, Filters
from openai import OpenAI
import json
from config import OPENAI_API_KEY
from db import get_user_tags, update_tag_weight, create_user_tag, update_user_preferences, get_user

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Define conversation states
WAITING_FOR_FEEDBACK_REASON = 0

def add_feedback_buttons(update: Update, context: CallbackContext, news_items):
    """Add feedback buttons to each news item"""
    
    # Store the news items in the user's context for later reference
    context.user_data['news_items'] = news_items
    
    for i, item in enumerate(news_items, 1):
        # Create unique callback data for this news item
        like_callback = f"like_{i}"
        dislike_callback = f"dislike_{i}"
        
        # Create inline keyboard with like/dislike buttons
        keyboard = [
            [
                InlineKeyboardButton("👍 Helpful", callback_data=like_callback),
                InlineKeyboardButton("👎 Not Relevant", callback_data=dislike_callback)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send the message with buttons
        update.message.reply_text(
            f"Was this news item relevant to your interests?",
            reply_markup=reply_markup
        )

def handle_feedback_callback(update: Update, context: CallbackContext) -> int:
    """Handle feedback button callbacks"""
    query = update.callback_query
    query.answer()
    
    callback_data = query.data
    user_id = str(update.effective_user.id)
    
    # Parse the callback data
    action, item_index = callback_data.split('_')
    item_index = int(item_index) - 1  # Convert to 0-based index
    
    # Get the news item that was rated
    news_items = context.user_data.get('news_items', [])
    if not news_items or item_index >= len(news_items):
        query.edit_message_text(text="Sorry, I couldn't find the news item you're rating.")
        return ConversationHandler.END
        
    rated_item = news_items[item_index]
    
    if action == "like":
        # For positive feedback, simply acknowledge and strengthen preferences
        query.edit_message_text(
            text=f"Thanks for the positive feedback! I'll keep bringing you similar content."
        )
        
        # Strengthen existing preferences for this content
        strengthen_preferences(user_id, rated_item)
        return ConversationHandler.END
        
    elif action == "dislike":
        # For negative feedback, ask for more details
        query.edit_message_text(
            text=f"I'm sorry this news wasn't relevant to you. Could you briefly tell me why?\n\n"
                 f"For example: \"Too technical\", \"Not my industry\", or \"Not about funding\""
        )
        
        # Store the rated item for later use
        context.user_data['rated_item'] = rated_item
        
        return WAITING_FOR_FEEDBACK_REASON
    
    return ConversationHandler.END

def process_feedback_reason(update: Update, context: CallbackContext) -> int:
    """Process the user's explanation for negative feedback"""
    user_id = str(update.effective_user.id)
    feedback_text = update.message.text
    rated_item = context.user_data.get('rated_item', {})
    
    if not rated_item:
        update.message.reply_text("Sorry, I couldn't find the news item you're giving feedback on.")
        return ConversationHandler.END
    
    # Let the user know we're processing
    update.message.reply_text("Analyzing your feedback... One moment please.")
    
    # Get current user preferences
    user_data = get_user(user_id)
    if not user_data or not user_data.get('preferences'):
        update.message.reply_text("Sorry, I couldn't find your preferences. Please use /start to set them up.")
        return ConversationHandler.END
        
    current_preferences = user_data.get('preferences', {})
    
    # Extract current interests for the AI
    current_interests = list(current_preferences.get('interests', {}).keys())
    
    # Use AI to analyze feedback and update preferences
    updated_preferences = analyze_feedback_with_ai(
        feedback_text, 
        rated_item,
        current_preferences,
        current_interests
    )
    
    if not updated_preferences:
        update.message.reply_text(
            "Thanks for your feedback. I'll try to improve my recommendations for you."
        )
        return ConversationHandler.END
    
    # Update the user's preferences in the database
    update_user_preferences(user_id, updated_preferences)
    
    # Update or create user tags based on new preferences
    for topic, weight in updated_preferences["interests"].items():
        create_user_tag(user_id, topic, weight)
    
    # Confirm changes
    added_interests = []
    removed_interests = []
    
    # Compare old and new interests to find what changed
    old_interests = set(current_preferences.get('interests', {}).keys())
    new_interests = set(updated_preferences.get('interests', {}).keys())
    
    added_interests = list(new_interests - old_interests)
    removed_interests = list(old_interests - new_interests)
    
    # Build response message
    response = "Thanks for your feedback! I've updated your preferences accordingly.\n\n"
    
    if added_interests:
        response += f"Added topics: {', '.join(added_interests)}\n"
    
    if removed_interests:
        response += f"Removed topics: {', '.join(removed_interests)}\n"
    
    if not added_interests and not removed_interests:
        response += "I've adjusted the importance of your existing interests based on your feedback."
    
    response += "\nYou'll see these changes reflected in your next news update. Type /news to try it out!"
    
    update.message.reply_text(response)
    return ConversationHandler.END

def strengthen_preferences(user_id, rated_item):
    """Strengthen preferences based on positive feedback"""
    try:
        # Get the user's current tags
        user_tags = get_user_tags(user_id)
        
        # If no tags, nothing to strengthen
        if not user_tags:
            return
        
        # Extract keywords from the news title
        title_words = rated_item.get('title', '').lower().split()
        
        # Simple keyword extraction - remove common words and keep potential topics
        common_words = ['a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'and', 'or']
        keywords = [word for word in title_words if word not in common_words and len(word) > 3]
        
        # For each existing tag, increase weight if it appears in the title
        for tag_data in user_tags:
            tag = tag_data.get('tag', '').lower()
            current_weight = tag_data.get('weight', 0.5)
            
            # If the tag appears in the title or keywords, increase its weight
            if tag in rated_item.get('title', '').lower() or tag in keywords:
                # Increase weight but cap at 1.0
                new_weight = min(1.0, current_weight + 0.1)
                
                # Update the tag weight
                update_tag_weight(user_id, tag, new_weight)
                logger.info(f"Increased weight for tag '{tag}' from {current_weight} to {new_weight}")
    
    except Exception as e:
        logger.error(f"Error strengthening preferences: {str(e)}")

def analyze_feedback_with_ai(feedback_text, news_item, current_preferences, current_interests):
    """Use AI to analyze feedback and update user preferences"""
    try:
        # Format current interests for AI prompt
        interests_string = ", ".join(current_interests) if current_interests else "None specified"
        
        # Create prompt for the AI
        prompt = f"""
        You are an AI preference analyzer for a news recommendation system.
        
        USER FEEDBACK ANALYSIS TASK:
        The user was shown this news article:
        - Title: {news_item.get('title', '')}
        - Source: {news_item.get('source', '')}
        
        The user indicated this was NOT relevant and provided this reason:
        "{feedback_text}"
        
        CURRENT USER PREFERENCES:
        - Current interests: {interests_string}
        - Role: {current_preferences.get('role', 'investor')}
        - Technical level: {current_preferences.get('technical_level', 'intermediate')}
        
        TASK:
        Based on the user's feedback, update their preference profile to better match their interests.
        
        1. Identify topics to ADD based on what they seem to want more of
        2. Identify topics to REMOVE that they're not interested in
        3. Adjust the weight of existing topics (from 0.0 to 1.0)
        4. Consider if their technical level or role should be adjusted
        
        Return a complete updated preference profile in JSON format that includes:
        {{
            "role": "string",
            "interests": {{"topic1": weight1, "topic2": weight2, ...}},
            "technical_level": "string",
            "preferred_sources": ["source1", "source2"],
            "recency_preference": number
        }}
        
        Maintain all existing preferences unless they directly conflict with the feedback.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI preference analyzer for a news recommendation system."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        updated_preferences = json.loads(response.choices[0].message.content)
        
        # Ensure the structure matches what we need
        if not isinstance(updated_preferences, dict):
            logger.error("AI returned invalid preferences format")
            return current_preferences
            
        # Ensure interests is a dictionary
        if "interests" not in updated_preferences or not isinstance(updated_preferences["interests"], dict):
            updated_preferences["interests"] = current_preferences.get("interests", {})
        
        # Copy over any fields that might not be in the AI response
        for key in current_preferences:
            if key not in updated_preferences:
                updated_preferences[key] = current_preferences[key]
                
        logger.info(f"Successfully updated preferences based on feedback")
        return updated_preferences
        
    except Exception as e:
        logger.error(f"Error analyzing feedback with AI: {str(e)}")
        # Return original preferences if AI analysis fails
        return current_preferences

def cancel_feedback(update: Update, context: CallbackContext) -> int:
    """Cancel the feedback conversation."""
    update.message.reply_text('Feedback cancelled.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
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
        
        # Log the callback data for debugging
        logger.info(f"Created feedback buttons with callback data: {like_callback}, {dislike_callback}")

def handle_feedback_callback(update: Update, context: CallbackContext) -> int:
    """Handle feedback button callbacks"""
    try:
        # Get the callback query
        query = update.callback_query
        query.answer()
        
        # Extract callback data
        callback_data = query.data
        logger.info(f"Received callback data: {callback_data}")
        
        # Retrieve the news items from context
        news_items = context.user_data.get('news_items', [])
        if not news_items:
            logger.error("No news items found in user context")
            query.edit_message_text("Error: Unable to process feedback.")
            return ConversationHandler.END
        
        # Handle like/dislike buttons
        if callback_data.startswith('like_'):
            try:
                # Extract the news item index
                index = int(callback_data.split('_')[1]) - 1
                selected_item = news_items[index]
                
                # Process like feedback
                strengthen_preferences(str(update.effective_user.id), selected_item)
                query.edit_message_text("Thank you for your feedback!")
                logger.info(f"Liked news item: {selected_item.get('title', 'Unknown')}")
                
                return ConversationHandler.END
                
            except (IndexError, ValueError) as e:
                logger.error(f"Error extracting news item index: {e}")
                query.edit_message_text("Error: Invalid news item.")
                return ConversationHandler.END
                
        elif callback_data.startswith('dislike_'):
            try:
                # Extract the news item index
                index = int(callback_data.split('_')[1]) - 1
                selected_item = news_items[index]
                
                # Store the rated item for future reference
                context.user_data['rated_item'] = selected_item
                
                # Prepare keyboard for feedback reasons
                keyboard = [
                    [InlineKeyboardButton("Too Technical", callback_data=f"reason_technical_{index+1}")],
                    [InlineKeyboardButton("Not Relevant", callback_data=f"reason_irrelevant_{index+1}")],
                    [InlineKeyboardButton("Already Knew", callback_data=f"reason_known_{index+1}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    "Why wasn't this news item helpful?", 
                    reply_markup=reply_markup
                )
                return WAITING_FOR_FEEDBACK_REASON
                
            except (IndexError, ValueError) as e:
                logger.error(f"Error extracting news item index: {e}")
                query.edit_message_text("Error: Invalid news item.")
                return ConversationHandler.END
                
        # Handle reason selection
        elif callback_data.startswith('reason_'):
            try:
                # Extract reason and index
                parts = callback_data.split('_')
                reason = parts[1]
                index = int(parts[2]) - 1
                selected_item = news_items[index]
                
                # Store the rated item and reason for further processing
                context.user_data['rated_item'] = selected_item
                context.user_data['feedback_reason'] = reason
                
                # Apply immediate feedback based on reason
                user_id = str(update.effective_user.id)
                
                # Process feedback with reason
                feedback_text = f"Not interested because it's {reason}"
                weaken_preferences(user_id, selected_item, feedback_text)
                
                # Get current user preferences
                user_data = get_user(user_id)
                if user_data and user_data.get('preferences'):
                    current_preferences = user_data.get('preferences', {})
                    current_interests = list(current_preferences.get('interests', {}).keys())
                    
                    # Use AI to analyze feedback and update preferences
                    updated_preferences = analyze_feedback_with_ai(
                        feedback_text, 
                        selected_item,
                        current_preferences,
                        current_interests
                    )
                    
                    if updated_preferences:
                        # Update the user's preferences in the database
                        update_user_preferences(user_id, updated_preferences)
                        
                        # Update or create user tags based on new preferences
                        for topic, weight in updated_preferences["interests"].items():
                            create_user_tag(user_id, topic, weight)
                
                # Log the specific reason
                logger.info(f"Dislike reason for '{selected_item.get('title', 'Unknown')}': {reason}")
                query.edit_message_text("Thank you for your detailed feedback! I'll improve my recommendations based on your preferences.")
                
                return ConversationHandler.END
                
            except (ValueError, IndexError) as e:
                logger.error(f"Error processing reason: {e}")
                query.edit_message_text("Error processing feedback.")
                return ConversationHandler.END
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error in handle_feedback_callback: {e}")
        query.edit_message_text("An error occurred while processing your feedback.")
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
    
    # Apply immediate weakening with the specific feedback text
    weaken_preferences(user_id, rated_item, feedback_text)
    
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

def weaken_preferences(user_id, rated_item, feedback_text=None):
    """Weaken preferences based on negative feedback"""
    try:
        # Get the user's current tags
        user_tags = get_user_tags(user_id)
        
        # If no tags, nothing to weaken
        if not user_tags:
            return
        
        # Extract keywords from the news title
        title = rated_item.get('title', '').lower()
        
        # Extract potential topics from the title
        title_words = title.split()
        common_words = ['a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'and', 'or']
        keywords = [word for word in title_words if word not in common_words and len(word) > 3]
        
        # For each existing tag, decrease weight if it appears in the title
        for tag_data in user_tags:
            tag = tag_data.get('tag', '').lower()
            current_weight = tag_data.get('weight', 0.5)
            
            # If the tag appears in the title or keywords, decrease its weight
            if tag in title or any(tag in keyword for keyword in keywords):
                # Decrease weight but not below 0.1
                new_weight = max(0.1, current_weight - 0.2)
                
                # Update the tag weight
                update_tag_weight(user_id, tag, new_weight)
                logger.info(f"Decreased weight for tag '{tag}' from {current_weight} to {new_weight}")
            
            # If feedback specifically mentions disinterest in a topic (e.g., "EU"), remove it
            if feedback_text and tag in feedback_text.lower() and any(neg in feedback_text.lower() for neg in ["don't", "not", "dislike"]):
                # Set a very low weight or delete the tag entirely
                update_tag_weight(user_id, tag, 0.1)  # Setting very low rather than deleting
                logger.info(f"Significantly decreased weight for rejected tag '{tag}' to 0.1")
    
    except Exception as e:
        logger.error(f"Error weakening preferences: {str(e)}")

def analyze_feedback_with_ai(feedback_text, news_item, current_preferences, current_interests):
    """Use AI to analyze feedback and update user preferences"""
    try:
        # Format current interests for AI prompt
        interests_string = ", ".join(current_interests) if current_interests else "None specified"
        
        # Extract key topics from the news item for better analysis
        news_title = news_item.get('title', '')
        news_source = news_item.get('source', '')
        
        # Create prompt for the AI with explicit instructions for negative feedback
        prompt = f"""
        You are an AI preference analyzer for a news recommendation system.
        
        USER FEEDBACK ANALYSIS TASK:
        The user was shown this news article:
        - Title: {news_title}
        - Source: {news_source}
        
        The user indicated this was NOT relevant and provided this reason:
        "{feedback_text}"
        
        CURRENT USER PREFERENCES:
        - Current interests: {interests_string}
        - Role: {current_preferences.get('role', 'investor')}
        - Technical level: {current_preferences.get('technical_level', 'intermediate')}
        
        IMPORTANT INSTRUCTIONS:
        1. If the user expresses dislike for a topic (e.g., "don't care about EU"), you MUST REMOVE all related topics
           (e.g., "eu_tech", "european_startups") from their interests.
        2. For any topics that appear in the news title but the user didn't like, DECREASE their weight by 0.3 or REMOVE them.
        3. DO NOT add new topics unless the user explicitly indicates interest in alternative topics.
        4. Be very careful with negative feedback - it usually means to REMOVE topics, not add them.
        5. This is critical: Never add a topic that the user has expressed disinterest in.
        
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
        
        # Special handling for geographic region rejections
        feedback_lower = feedback_text.lower()
        regions = ["eu", "europe", "european", "us", "usa", "america", "american", "china", "chinese", 
                  "asia", "asian", "africa", "african", "middle east", "latin america"]
        
        # If user expressed disinterest in a region, ensure all related topics are removed
        for region in regions:
            if (f"don't care about {region}" in feedback_lower or 
                f"not interested in {region}" in feedback_lower or 
                f"don't like {region}" in feedback_lower):
                
                # Remove any topics containing the region name
                interests_to_remove = []
                for topic in updated_preferences["interests"].keys():
                    if region in topic.lower():
                        interests_to_remove.append(topic)
                
                # Remove identified topics
                for topic in interests_to_remove:
                    if topic in updated_preferences["interests"]:
                        del updated_preferences["interests"][topic]
                
                logger.info(f"Removed {len(interests_to_remove)} region-related topics based on feedback")
        
        # Double check that we haven't accidentally added topics that should be removed
        # (This is a safety check against AI misinterpreting the feedback)
        if "cloud" in feedback_lower and "don't" in feedback_lower:
            interests_to_remove = [topic for topic in updated_preferences["interests"] if "cloud" in topic.lower()]
            for topic in interests_to_remove:
                if topic in updated_preferences["interests"]:
                    del updated_preferences["interests"][topic]
        
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
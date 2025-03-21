# db.py - Database interactions

from supabase import create_client
import logging
from datetime import datetime
import json
from config import SUPABASE_URL, SUPABASE_KEY, DEFAULT_NEWS_SYSTEM_MESSAGE, DEFAULT_TWITTER_SYSTEM_MESSAGE

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Supabase client with custom options to avoid proxy parameter
from supabase.lib.client_options import ClientOptions
options = ClientOptions()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)

def get_or_create_user(user_id, username=None, first_name=None):
    """Get user data or create if not exists"""
    try:
        # Try to get the user
        response = supabase.table('users').select('*').eq('id', str(user_id)).execute()
        
        if response.data and len(response.data) > 0:
            logger.info(f"Found existing user: {user_id}")
            return response.data[0]
        
        # User doesn't exist, create new
        logger.info(f"Creating new user: {user_id}")
        user_data = {
            "id": str(user_id),
            "username": username,
            "first_name": first_name,
            "created_at": datetime.now().isoformat(),
            "preferences": {
                "service_type": None,
                "news_system_message": DEFAULT_NEWS_SYSTEM_MESSAGE,
                "twitter_system_message": DEFAULT_TWITTER_SYSTEM_MESSAGE,
                "excluded_topics": [],
                "excluded_twitter_accounts": []
            }
        }
        
        response = supabase.table('users').insert(user_data).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            logger.error(f"Failed to create user: {user_id}")
            return None
            
    except Exception as e:
        logger.error(f"Database error in get_or_create_user: {str(e)}")
        return None

def update_user_service_choice(user_id, service_type):
    """Update the user's service choice (news or twitter)"""
    try:
        response = supabase.table('users').update({
            "preferences": {
                "service_type": service_type
            }
        }).eq('id', str(user_id)).execute()
        
        return response.data[0] if response.data else None
        
    except Exception as e:
        logger.error(f"Database error in update_user_service_choice: {str(e)}")
        return None

def update_user_system_message(user_id, service_type, system_message):
    """Update the user's customized system message for the specified service"""
    try:
        # First get current preferences
        response = supabase.table('users').select('preferences').eq('id', str(user_id)).execute()
        if not response.data or not response.data[0].get('preferences'):
            logger.error(f"No preferences found for user: {user_id}")
            return None
            
        # Update the specific system message while preserving other preferences
        preferences = response.data[0]['preferences']
        
        if service_type == 'news':
            preferences['news_system_message'] = system_message
        elif service_type == 'twitter':
            preferences['twitter_system_message'] = system_message
        
        # Save updated preferences
        response = supabase.table('users').update({
            "preferences": preferences
        }).eq('id', str(user_id)).execute()
        
        return response.data[0] if response.data else None
        
    except Exception as e:
        logger.error(f"Database error in update_user_system_message: {str(e)}")
        return None

def get_user_system_message(user_id, service_type):
    """Get the user's customized system message for the specified service"""
    try:
        response = supabase.table('users').select('preferences').eq('id', str(user_id)).execute()
        
        if response.data and response.data[0].get('preferences'):
            preferences = response.data[0]['preferences']
            
            if service_type == 'news':
                return preferences.get('news_system_message', DEFAULT_NEWS_SYSTEM_MESSAGE)
            elif service_type == 'twitter':
                return preferences.get('twitter_system_message', DEFAULT_TWITTER_SYSTEM_MESSAGE)
        
        # Return default if not found
        if service_type == 'news':
            return DEFAULT_NEWS_SYSTEM_MESSAGE
        else:
            return DEFAULT_TWITTER_SYSTEM_MESSAGE
            
    except Exception as e:
        logger.error(f"Database error in get_user_system_message: {str(e)}")
        # Return default in case of error
        if service_type == 'news':
            return DEFAULT_NEWS_SYSTEM_MESSAGE
        else:
            return DEFAULT_TWITTER_SYSTEM_MESSAGE

def update_excluded_items(user_id, service_type, item, add=True):
    """Add or remove an excluded item (topic/twitter account) for a user"""
    try:
        # First get current preferences
        response = supabase.table('users').select('preferences').eq('id', str(user_id)).execute()
        if not response.data or not response.data[0].get('preferences'):
            logger.error(f"No preferences found for user: {user_id}")
            return None
            
        # Update the excluded items while preserving other preferences
        preferences = response.data[0]['preferences']
        
        if service_type == 'news':
            excluded_list = preferences.get('excluded_topics', [])
        else:  # twitter
            excluded_list = preferences.get('excluded_twitter_accounts', [])
        
        # Add or remove item
        if add and item not in excluded_list:
            excluded_list.append(item)
        elif not add and item in excluded_list:
            excluded_list.remove(item)
        
        # Update the list in preferences
        if service_type == 'news':
            preferences['excluded_topics'] = excluded_list
        else:  # twitter
            preferences['excluded_twitter_accounts'] = excluded_list
        
        # Save updated preferences
        response = supabase.table('users').update({
            "preferences": preferences
        }).eq('id', str(user_id)).execute()
        
        return response.data[0] if response.data else None
        
    except Exception as e:
        logger.error(f"Database error in update_excluded_items: {str(e)}")
        return None

def log_user_feedback(user_id, service_type, content_id, feedback_type, feedback_reason=None):
    """Log user feedback on content"""
    try:
        feedback_data = {
            "user_id": str(user_id),
            "service_type": service_type,
            "content_id": content_id,
            "feedback_type": feedback_type,
            "feedback_reason": feedback_reason,
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table('user_feedback').insert(feedback_data).execute()
        return response.data[0] if response.data else None
        
    except Exception as e:
        logger.error(f"Database error in log_user_feedback: {str(e)}")
        return None
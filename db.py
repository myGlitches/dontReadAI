from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
import logging
import hashlib
from datetime import datetime

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

viewed_news_memory = {}

def get_user(user_id):
    """Get user data from Supabase"""
    response = supabase.table('users').select('*').eq('id', str(user_id)).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None

def create_user(user_id, name, preferences=None):
    """Create a new user in Supabase"""
    if preferences is None:
        preferences = {"platforms": ["twitter"], "interest": "AI"}
    
    user_data = {
        "id": str(user_id),
        "name": name,
        "preferences": preferences
    }
    
    response = supabase.table('users').insert(user_data).execute()
    return response.data[0] if response.data else None

def get_user_tags(user_id):
    """Get all tags for a user from preferences"""
    user = get_user(user_id)
    if not user or 'preferences' not in user:
        return {}
    
    return user['preferences'].get('interests', {})    

def update_user_tags(user_id, tags_dict):
    """Update user tags all at once in the preferences field"""
    # Get current preferences
    user = get_user(user_id)
    preferences = user.get('preferences', {}) if user else {}
    
    # Update the interests section
    preferences['interests'] = tags_dict
    
    # Save back to database
    return update_user_preferences(user_id, preferences)

def update_user_preferences(user_id, preferences):
    """Update user preferences in Supabase"""
    response = supabase.table('users').update({"preferences": preferences}).eq('id', str(user_id)).execute()
    return response.data[0] if response.data else None

def create_user_tag(user_id, tag, weight=1.0):
    """Create a new tag for a user in preferences directly"""
    # Get current preferences
    user = get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found when creating tag")
        return None
        
    preferences = user.get('preferences', {})
    
    # Make sure interests exists
    if 'interests' not in preferences:
        preferences['interests'] = {}
    
    # Add or update the tag
    preferences['interests'][tag] = weight
    
    # Save back to database
    return update_user_preferences(user_id, preferences)

def update_tag_weight(user_id, tag, new_weight):
    """Update the weight of a user tag"""
    # Get current preferences
    user = get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found when updating tag weight")
        return None
        
    preferences = user.get('preferences', {})
    
    # Make sure interests exists
    if 'interests' not in preferences:
        preferences['interests'] = {}
    
    # Update the tag weight if it exists
    if tag in preferences['interests']:
        preferences['interests'][tag] = new_weight
        
    # Save back to database
    return update_user_preferences(user_id, preferences)

def delete_user_tags(user_id):
    """Clear user tags by updating preferences"""
    user = get_user(user_id)
    if not user:
        return None
        
    preferences = user.get('preferences', {})
    preferences['interests'] = {}
    
    return update_user_preferences(user_id, preferences)

def generate_news_id(news_item):
    """Generate a unique ID for a news item based on title and URL"""
    content_to_hash = f"{news_item['title']}|{news_item.get('url', '')}"
    return hashlib.md5(content_to_hash.encode()).hexdigest()

def add_viewed_news(user_id, news_item):
    """Record that a user has viewed a specific news item"""
    news_id = generate_news_id(news_item)
    
    # First try with the database table
    try:
        viewed_data = {
            "user_id": str(user_id),
            "news_id": news_id,
            "title": news_item['title'][:100],  # Store title for reference
            "viewed_at": datetime.now().isoformat()
        }
        
        response = supabase.table('user_viewed_news').insert(viewed_data).execute()
        return response.data[0] if response.data else None
        
    except Exception as e:
        logger.warning(f"DB operation failed, using memory fallback: {str(e)}")
        
        # Fallback to in-memory storage if table doesn't exist
        if user_id not in viewed_news_memory:
            viewed_news_memory[user_id] = []
            
        viewed_news_memory[user_id].append({
            "news_id": news_id,
            "title": news_item['title'][:100],
            "viewed_at": datetime.now().isoformat()
        })
        
        return {"news_id": news_id}

def has_viewed_news(user_id, news_item):
    """Check if a user has already viewed a specific news item"""
    news_id = generate_news_id(news_item)
    
    # First try with the database table
    try:
        response = supabase.table('user_viewed_news') \
                         .select('*') \
                         .eq('user_id', str(user_id)) \
                         .eq('news_id', news_id) \
                         .execute()
        
        return bool(response.data and len(response.data) > 0)
        
    except Exception as e:
        logger.warning(f"DB operation failed, using memory fallback: {str(e)}")
        
        # Fallback to in-memory storage if table doesn't exist
        if user_id in viewed_news_memory:
            for item in viewed_news_memory[user_id]:
                if item["news_id"] == news_id:
                    return True
        
        return False

def get_user_history(user_id, limit=20):
    """Get the user's recently viewed news items"""
    try:
        response = supabase.table('user_viewed_news') \
                         .select('*') \
                         .eq('user_id', str(user_id)) \
                         .order('viewed_at', desc=True) \
                         .limit(limit) \
                         .execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        logger.warning(f"DB operation failed, using memory fallback: {str(e)}")
        
        # Fallback to in-memory storage
        if user_id in viewed_news_memory:
            # Sort by viewed_at in descending order
            sorted_items = sorted(
                viewed_news_memory[user_id], 
                key=lambda x: x.get('viewed_at', ''),
                reverse=True
            )
            return sorted_items[:limit]
        
        return []

def clear_user_history(user_id):
    """Clear a user's viewing history"""
    try:
        response = supabase.table('user_viewed_news') \
                         .delete() \
                         .eq('user_id', str(user_id)) \
                         .execute()
        
        # Also clear memory storage
        if user_id in viewed_news_memory:
            viewed_news_memory[user_id] = []
            
        return response.data if response.data else []
        
    except Exception as e:
        logger.warning(f"DB operation failed, using memory fallback: {str(e)}")
        
        # Clear memory storage
        if user_id in viewed_news_memory:
            viewed_news_memory[user_id] = []
            
        return []
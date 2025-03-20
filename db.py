# /db.py
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
import logging

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def create_user_tag(user_id, tag, weight=0.7):
    """Create a new tag for a user"""
    try:
        tag_data = {
            "user_id": str(user_id),
            "tag": tag.lower(),
            "weight": weight
        }
        
        response = supabase.table('user_tags').insert(tag_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating user tag: {str(e)}")
        return None
    
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
    """Create a new tag for a user, with conflict handling."""
    tag_data = {
        "user_id": user_id,
        "tag": tag,
        "weight": weight
    }
    
    try:
        # Try to delete any existing tag with the same name first
        supabase.table('user_tags').delete().eq('user_id', user_id).eq('tag', tag).execute()
        
        # Then insert the new tag
        response = supabase.table('user_tags').insert(tag_data).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error creating user tag: {str(e)}")
        # If there was an error, try updating instead
        try:
            response = supabase.table('user_tags').update({"weight": weight}).eq('user_id', user_id).eq('tag', tag).execute()
            return response.data
        except Exception as e2:
            logger.error(f"Error updating user tag: {str(e2)}")
            return None

def get_user_tags(user_id):
    """Get all tags for a user from preferences"""
    user = get_user(user_id)
    if not user or 'preferences' not in user:
        return {}
    
    return user['preferences'].get('interests', {})

def update_tag_weight(user_id, tag, new_weight):
    """Update the weight of a user tag"""
    response = supabase.table('user_tags').update({"weight": new_weight}).eq('user_id', str(user_id)).eq('tag', tag.lower()).execute()
    return response.data[0] if response.data else None

def delete_user_tags(user_id):
    """Clear user tags by updating preferences"""
    user = get_user(user_id)
    if not user:
        return None
        
    preferences = user.get('preferences', {})
    preferences['interests'] = {}
    
    return update_user_preferences(user_id, preferences)
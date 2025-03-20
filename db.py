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

def update_user_preferences(user_id, preferences):
    """Update user preferences in Supabase"""
    response = supabase.table('users').update({"preferences": preferences}).eq('id', str(user_id)).execute()
    return response.data[0] if response.data else None

def create_user_tag(user_id, tag, weight=0.7):
    """Create a new tag for a user"""
    tag_data = {
        "user_id": str(user_id),
        "tag": tag.lower(),
        "weight": weight
    }
    
    response = supabase.table('user_tags').insert(tag_data).execute()
    return response.data[0] if response.data else None

def get_user_tags(user_id):
    """Get all tags for a user"""
    response = supabase.table('user_tags').select('*').eq('user_id', str(user_id)).execute()
    return response.data if response.data else []

def update_tag_weight(user_id, tag, new_weight):
    """Update the weight of a user tag"""
    response = supabase.table('user_tags').update({"weight": new_weight}).eq('user_id', str(user_id)).eq('tag', tag.lower()).execute()
    return response.data[0] if response.data else None
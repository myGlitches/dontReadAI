from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

def update_user_preferences(user_id, preferences):
    """Update user preferences in Supabase"""
    response = supabase.table('users').update({"preferences": preferences}).eq('id', str(user_id)).execute()
    return response.data[0] if response.data else None
# preferences.py
from db import get_user, update_user_preferences
from utils import extract_topics_from_news, extract_region_from_news

def initialize_preferences(user_id, preference_type="ai_funding"):
    """Set up initial user preferences"""
    if preference_type == "ai_funding":
        return {
            "interests": {"ai_funding": 1.0, "startups": 0.8},
            "exclusions": [],  # Topics user explicitly doesn't want
            "technical_level": "intermediate"
        }
    # Can add other preference types later

def update_preferences_from_feedback(user_id, news_item, feedback_type, reason=None):
    """Update preferences based on user feedback"""
    user = get_user(user_id)
    preferences = user.get("preferences", {})
    
    # Extract topics from the news item
    topics = extract_topics_from_news(news_item)
    
    if feedback_type == "like":
        # Strengthen interest in these topics
        for topic in topics:
            if topic in preferences["interests"]:
                preferences["interests"][topic] = min(1.0, preferences["interests"][topic] + 0.1)
            else:
                preferences["interests"][topic] = 0.7
    
    elif feedback_type == "dislike":
        # Handle dislike with reason
        if reason == "not_interested_region":
            # Extract region and add to exclusions
            region = extract_region_from_news(news_item)
            if region and region not in preferences["exclusions"]:
                preferences["exclusions"].append(region)
        
        # Weaken interest in these topics
        for topic in topics:
            if topic in preferences["interests"]:
                preferences["interests"][topic] = max(0.1, preferences["interests"][topic] - 0.2)
    
    # Save updated preferences
    update_user_preferences(user_id, preferences)
    return preferences
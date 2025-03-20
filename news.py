# /news.py
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_ai_tech_news(user_preferences=None):
    """Fetch AI news from HackerNews API, filtered by user preferences"""
    # Get top stories
    response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    if response.status_code != 200:
        return []
        
    story_ids = response.json()[:50]  # Get top 50 stories for better filtering potential
    
    ai_stories = []
    
    # Define AI keywords to ensure content is AI-related
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'llm', 
                  'gpt', 'chatgpt', 'openai', 'anthropic', 'claude']
                  
    # Define funding keywords for the funding option
    funding_keywords = ['funding', 'investment', 'raises', 'venture', 'capital', 'million', 
                       'billion', 'series a', 'series b', 'seed round', 'vc', 'investor']
    
    # Check if funding filter is enabled
    funding_filter = False
    if user_preferences and user_preferences.get('news_focus') == 'funding':
        funding_filter = True
    
    # Process stories
    for story_id in story_ids:
        story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        if story_response.status_code != 200:
            continue
            
        story = story_response.json()
        
        # Skip stories without a title or URL
        if not story.get('title') or not story.get('url'):
            continue
        
        title = story.get('title', '').lower()
        text = story.get('text', '').lower() if story.get('text') else ''
        content = title + " " + text
        
        # First check if it's AI-related (basic filter)
        is_ai_related = any(keyword in content for keyword in ai_keywords)
        
        # Skip if not AI-related at all
        if not is_ai_related:
            continue
        
        # Apply funding filter if enabled
        if funding_filter:
            is_funding_related = any(keyword in content for keyword in funding_keywords)
            # Skip if not funding-related
            if not is_funding_related:
                continue
        
        # Calculate relevance score
        relevance_score = 1.0  # Default score
        
        # If we have user interests, boost relevance for matching keywords
        if user_preferences and 'interests' in user_preferences:
            for keyword, weight in user_preferences['interests'].items():
                if keyword.lower() in content:
                    relevance_score += weight
        
        # Give bonus relevance for funding keywords if that's the focus
        if funding_filter:
            for keyword in funding_keywords:
                if keyword in content:
                    relevance_score += 0.5
                    # Extra boost for funding terms in the title
                    if keyword in title:
                        relevance_score += 0.5
        
        ai_stories.append({
            'title': story.get('title'),
            'url': story.get('url'),
            'score': story.get('score', 0),
            'source': 'HackerNews',
            'relevance': relevance_score
        })
    
    # Sort by relevance first, then by score
    sorted_stories = sorted(ai_stories, key=lambda x: (x.get('relevance', 0), x.get('score', 0)), reverse=True)
    
    # If no stories match with funding filter, consider falling back to general AI
    if funding_filter and not sorted_stories:
        # Log this situation
        logger.info("No funding stories found, may need to implement fallback logic")
        
    return sorted_stories[:5]
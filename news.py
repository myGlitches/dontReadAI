# /news.py
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_ai_tech_news(user_preferences=None):
    """Fetch AI news from HackerNews API, focused on AI funding news"""
    # Get top stories
    response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    if response.status_code != 200:
        return []
        
    story_ids = response.json()[:50]  # Get top 50 stories for better filtering potential
    
    ai_stories = []
    
    # Define AI keywords to ensure content is AI-related
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'llm', 
                  'gpt', 'chatgpt', 'openai', 'anthropic', 'claude']
                  
    # Define funding keywords - these are always applied since we're focusing on funding
    funding_keywords = ['funding', 'investment', 'raises', 'venture', 'capital', 'million', 
                       'billion', 'series a', 'series b', 'seed round', 'vc', 'investor']
    
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
        
        # Check if it's AI-related
        is_ai_related = any(keyword in content for keyword in ai_keywords)
        
        # Skip if not AI-related
        if not is_ai_related:
            continue
        
        # Check if it's funding-related (we're only interested in funding news)
        is_funding_related = any(keyword in content for keyword in funding_keywords)
        
        # Skip if not funding-related
        if not is_funding_related:
            continue
        
        # Calculate relevance score
        relevance_score = 1.0  # Base score
        
        # Give extra points for funding terms in the title (more relevant)
        for keyword in funding_keywords:
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
    
    # If no stories found, add a placeholder message
    if not sorted_stories:
        logger.info("No funding stories found in current data")
        
    return sorted_stories[:5]
# /news.py
import requests

def fetch_ai_tech_news(user_preferences=None):
    """Fetch AI news from HackerNews API, filtered by user preferences"""
    # Get top stories
    response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    if response.status_code != 200:
        return []
        
    story_ids = response.json()[:30]  # Get top 30 stories
    
    ai_stories = []
    for story_id in story_ids:
        story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        if story_response.status_code != 200:
            continue
            
        story = story_response.json()
        
        # Skip stories without a title or URL
        if not story.get('title') or not story.get('url'):
            continue
        
        # Basic filtering for AI/tech related content
        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'llm', 
                      'gpt', 'chatgpt', 'openai', 'anthropic', 'claude']
        
        # Add user's interest keywords if available
        if user_preferences and 'interests' in user_preferences:
            user_keywords = [k.lower() for k in user_preferences['interests'].keys()]
            ai_keywords.extend(user_keywords)
            
        title = story.get('title', '').lower()
        if any(keyword in title for keyword in ai_keywords):
            # Calculate relevance score if we have user preferences
            relevance_score = 1.0  # Default score
            
            if user_preferences and 'interests' in user_preferences:
                relevance_score = 0.1  # Base score
                
                # Check for interest keyword matches
                for keyword, weight in user_preferences['interests'].items():
                    if keyword.lower() in title:
                        relevance_score += weight
            
            ai_stories.append({
                'title': story.get('title'),
                'url': story.get('url'),
                'score': story.get('score', 0),
                'source': 'HackerNews',
                'relevance': relevance_score
            })
    
    # Sort by relevance first, then by score
    return sorted(ai_stories, key=lambda x: (x.get('relevance', 0), x.get('score', 0)), reverse=True)[:5]
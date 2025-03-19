import requests

def fetch_ai_tech_news():
    """Fetch AI news from HackerNews API"""
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
        
        # Basic filtering for AI/tech related content
        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'llm', 
                      'gpt', 'chatgpt', 'openai', 'anthropic', 'claude']
        
        # Skip stories without a title or URL
        if not story.get('title') or not story.get('url'):
            continue
            
        title = story.get('title', '').lower()
        if any(keyword in title for keyword in ai_keywords):
            ai_stories.append({
                'title': story.get('title'),
                'url': story.get('url'),
                'score': story.get('score', 0),
                'source': 'HackerNews'
            })
    
    # Sort by score and return top 5
    return sorted(ai_stories, key=lambda x: x.get('score', 0), reverse=True)[:5]
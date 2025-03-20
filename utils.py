# utils.py - Helper functions for our news system

import re
from openai import OpenAI
from config import OPENAI_API_KEY

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def extract_topics_from_news(news_item):
    """Extract relevant topics from a news item"""
    # Option 1: Simple keyword extraction
    keywords = []
    title = news_item.get('title', '').lower()
    
    # AI-related keywords
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'llm', 
                  'gpt', 'deep learning', 'neural network']
    
    # Funding-related keywords
    funding_keywords = ['funding', 'investment', 'raises', 'venture', 'capital', 
                       'million', 'billion', 'series a', 'series b', 'seed']
    
    # Technology domains
    tech_domains = ['nlp', 'computer vision', 'robotics', 'generative ai', 
                   'autonomous', 'cloud', 'saas']
    
    # Check for keywords in title
    for keyword in ai_keywords + funding_keywords + tech_domains:
        if keyword in title and keyword not in keywords:
            keywords.append(keyword)
    
    # Option 2: Use OpenAI for more sophisticated extraction
    if len(keywords) < 2:  # If simple extraction didn't find much
        try:
            prompt = f"""
            Extract 3-5 key topics from this AI funding news:
            Title: {news_item.get('title')}
            Focus on: AI domains, funding stages, technology areas
            Return as a comma-separated list.
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            
            ai_keywords = response.choices[0].message.content.split(',')
            ai_keywords = [k.strip().lower() for k in ai_keywords]
            
            # Add these to our keywords
            for k in ai_keywords:
                if k and k not in keywords:
                    keywords.append(k)
        except Exception as e:
            print(f"Error using AI for keyword extraction: {e}")
    
    return keywords

def extract_region_from_news(news_item):
    """Extract geographic regions from a news item"""
    title = news_item.get('title', '')
    
    # Common regions/countries
    regions = {
        'us': ['us', 'usa', 'united states', 'american'],
        'eu': ['eu', 'europe', 'european union', 'european'],
        'uk': ['uk', 'united kingdom', 'britain', 'british'],
        'china': ['china', 'chinese'],
        'india': ['india', 'indian'],
        'japan': ['japan', 'japanese'],
        'canada': ['canada', 'canadian'],
        'australia': ['australia', 'australian'],
        'africa': ['africa', 'african'],
        'latam': ['latin america', 'latam', 'brazil', 'mexico']
    }
    
    # Check title for regions
    for region, keywords in regions.items():
        for keyword in keywords:
            if keyword in title.lower():
                return region
    
    return None

def fetch_from_hackernews():
    """Fetch AI funding news from HackerNews API"""
    import requests
    import time
    from datetime import datetime
    
    try:
        response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        if response.status_code != 200:
            return []
            
        story_ids = response.json()[:30]  # Get top 30 stories
        
        stories = []
        for story_id in story_ids:
            try:
                story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                if story_response.status_code != 200:
                    continue
                    
                story = story_response.json()
                
                # Skip stories without a title or URL
                if not story.get('title') or not story.get('url'):
                    continue
                
                # Convert timestamp to date
                timestamp = story.get('time', 0)
                date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                
                stories.append({
                    'title': story.get('title'),
                    'url': story.get('url'),
                    'date': date,
                    'source': 'HackerNews'
                })
                
                # Add a small delay
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Error processing HackerNews story: {e}")
                
        return stories
        
    except Exception as e:
        print(f"Error fetching from HackerNews: {e}")
        return []

def fetch_from_techcrunch():
    """Fetch news from TechCrunch RSS feed"""
    import requests
    from bs4 import BeautifulSoup
    from datetime import datetime
    
    try:
        response = requests.get("https://techcrunch.com/feed/")
        if response.status_code != 200:
            return []
        
        # Parse XML
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        stories = []
        for item in items:
            try:
                # Extract date
                pub_date = item.pubDate.text
                date_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                date = date_obj.strftime('%Y-%m-%d')
                
                stories.append({
                    'title': item.title.text,
                    'url': item.link.text,
                    'date': date,
                    'source': 'TechCrunch'
                })
            except Exception as e:
                print(f"Error processing TechCrunch item: {e}")
        
        return stories
        
    except Exception as e:
        print(f"Error fetching from TechCrunch: {e}")
        return []

def filter_by_keywords(news_items):
    """Filter news items based on AI and funding keywords"""
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'llm', 
                  'gpt', 'chatgpt', 'deep learning', 'neural network']
                  
    funding_keywords = ['funding', 'investment', 'raises', 'venture', 'capital', 'million', 
                       'billion', 'series a', 'series b', 'seed round']
    
    filtered_items = []
    
    for item in news_items:
        title = item.get('title', '').lower()
        
        # Check if it contains AI keywords
        has_ai = any(keyword in title for keyword in ai_keywords)
        
        # Check if it contains funding keywords
        has_funding = any(keyword in title for keyword in funding_keywords)
        
        # Include if it has both AI and funding references
        if has_ai and has_funding:
            filtered_items.append(item)
    
    return filtered_items

def rank_news_by_relevance(news_items, user_preferences):
    """Rank news items by relevance to user preferences"""
    user_interests = user_preferences.get('interests', {})
    ranked_items = []
    
    for item in news_items:
        # Extract topics from the news item
        topics = extract_topics_from_news(item)
        
        # Calculate relevance score
        relevance_score = 0
        
        for topic in topics:
            # Check if this topic is in user interests
            for interest, weight in user_interests.items():
                if topic in interest or interest in topic:
                    relevance_score += weight
        
        # Add relevance score to the item
        item['relevance_score'] = relevance_score
        ranked_items.append(item)
    
    # Sort by relevance score (descending)
    ranked_items.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    return ranked_items


def help_command(update, context):
    """Show help information"""
    help_text = (
        "🤖 *AI Funding News Bot* 🤖\n\n"
        "Get personalized AI funding and investment news.\n\n"
        "*Available Commands:*\n"
        "/start - Initialize the bot and set up preferences\n"
        "/news - Get your personalized AI funding news\n"
        # "/interests - View your current interest topics\n"
        # "/add_tag <tag> [weight] - Add a new interest (e.g., /add_tag computer_vision 0.9)\n"
        # "/remove_tag <tag> - Remove an interest (e.g., /remove_tag blockchain)\n"
        # "/adjust_interest <tag> <weight> - Change priority of an interest\n"
        "/history - View your recently read news\n"
        "/clear_history - Clear your news history\n"
        "/reset - Reset your preferences and start over\n"
        "/help - Show this help message\n\n"
        "You can also provide feedback on news items to improve recommendations."
    )
    
    update.message.reply_text(help_text, parse_mode='Markdown')
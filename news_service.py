# news_service.py - AI Funding News Service

import requests
import logging
import hashlib
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from openai import OpenAI
from config import OPENAI_API_KEY
from db import get_user_system_message

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_ai_funding_news():
    """Fetch AI funding news from multiple sources"""
    news_items = []
    
    # Add news from HackerNews
    news_items.extend(fetch_from_hackernews())
    
    # Add news from TechCrunch
    news_items.extend(fetch_from_techcrunch())
    
    # Filter for AI funding news
    filtered_news = filter_ai_funding_news(news_items)
    
    logger.info(f"Fetched {len(filtered_news)} AI funding news items")
    return filtered_news

def fetch_from_hackernews():
    """Fetch potential AI funding news from HackerNews"""
    logger.info("Fetching from HackerNews")
    news_items = []
    
    try:
        # Get top stories
        response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        if response.status_code != 200:
            logger.error(f"Failed to fetch HackerNews top stories: {response.status_code}")
            return []
            
        # Take top 100 stories to increase chances of finding AI funding news
        story_ids = response.json()[:100]
        
        for story_id in story_ids:
            try:
                story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                if story_response.status_code != 200:
                    continue
                    
                story = story_response.json()
                
                # Skip stories without title or URL
                if not story.get('title') or not story.get('url'):
                    continue
                
                # Create news item
                news_items.append({
                    'id': str(story_id),
                    'title': story.get('title'),
                    'url': story.get('url'),
                    'source': 'HackerNews',
                    'date': datetime.fromtimestamp(story.get('time', 0)).strftime('%Y-%m-%d')
                })
                
            except Exception as e:
                logger.error(f"Error processing HackerNews story {story_id}: {str(e)}")
                continue
                
        logger.info(f"Fetched {len(news_items)} items from HackerNews")
        return news_items
        
    except Exception as e:
        logger.error(f"Error fetching from HackerNews: {str(e)}")
        return []

def fetch_from_techcrunch():
    """Fetch potential AI funding news from TechCrunch"""
    logger.info("Fetching from TechCrunch")
    news_items = []
    
    try:
        # Get RSS feed
        response = requests.get("https://techcrunch.com/feed/")
        if response.status_code != 200:
            logger.error(f"Failed to fetch TechCrunch RSS: {response.status_code}")
            return []
            
        # Parse XML
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        for item in items:
            try:
                # Get item details
                title = item.title.text
                link = item.link.text
                pub_date = item.pubDate.text
                
                # Parse date
                date_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                date = date_obj.strftime('%Y-%m-%d')
                
                # Create ID from title and link
                item_id = hashlib.md5(f"{title}|{link}".encode()).hexdigest()
                
                # Create news item
                news_items.append({
                    'id': item_id,
                    'title': title,
                    'url': link,
                    'source': 'TechCrunch',
                    'date': date
                })
                
            except Exception as e:
                logger.error(f"Error processing TechCrunch item: {str(e)}")
                continue
                
        logger.info(f"Fetched {len(news_items)} items from TechCrunch")
        return news_items
        
    except Exception as e:
        logger.error(f"Error fetching from TechCrunch: {str(e)}")
        return []

def filter_ai_funding_news(news_items):
    """Filter news to only include AI funding related items"""
    ai_funding_items = []
    
    # Define keywords for initial filtering
    ai_terms = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning',
                'neural network', 'gpt', 'llm', 'large language model']
                
    funding_terms = ['fund', 'invest', 'raise', 'capital', 'venture', 'million', 'billion', 
                     'series', 'seed', 'acquisition', 'acquires', 'acquired']
    
    # First-pass filtering based on keywords
    for item in news_items:
        title_lower = item['title'].lower()
        
        # Check if title contains both AI and funding terms
        has_ai_term = any(term in title_lower for term in ai_terms)
        has_funding_term = any(term in title_lower for term in funding_terms)
        
        if has_ai_term and has_funding_term:
            ai_funding_items.append(item)
            logger.info(f"Identified AI funding news: {item['title']}")
            
    logger.info(f"Filtered to {len(ai_funding_items)} AI funding news items")
    return ai_funding_items

def get_news_content(url):
    """Fetch and extract article content"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AINewsBot/1.0)'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove noise elements
        for element in soup.select('nav, header, footer, aside, script, style, .ads, .comments'):
            if element:
                element.extract()
        
        # Try to find main article content
        content_selectors = [
            'article', '.article-content', '.entry-content', '.post-content',
            '.article-body', 'main', '#content', '.story'
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content and len(content.get_text(strip=True)) > 300:
                return ' '.join(content.get_text(strip=True).split())
        
        # Fallback to body content
        body_text = soup.body.get_text(strip=True)
        return ' '.join(body_text.split())
        
    except Exception as e:
        logger.error(f"Error fetching article content from {url}: {str(e)}")
        return ""

def generate_news_summary(user_id, news_items):
    """Generate a summary of AI funding news for a user"""
    if not news_items:
        logger.warning("No news items to summarize")
        return "No AI funding news found today."
    
    # Get user's customized system message
    system_message = get_user_system_message(user_id, 'news')
    
    # Prepare news data for the prompt
    news_data = []
    for item in news_items[:10]:  # Limit to top 10 items
        # Get article content
        content = get_news_content(item['url'])
        
        news_data.append({
            'title': item['title'],
            'url': item['url'],
            'source': item['source'],
            'date': item['date'],
            'content_preview': content[:3000]  # Limit content size
        })
    
    # Create prompt for the AI
    user_prompt = f"""
    Generate a comprehensive summary of these AI funding news articles.
    Focus on extracting key information about each funding event, including:
    - Company name
    - Funding amount and round (Series A, B, etc.)
    - Investors
    - What the company does
    - How they plan to use the funding
    
    Articles to summarize:
    {news_data}
    
    Format your response as a concise news briefing with clear sections for each major funding event.
    At the end, include a list of links to the original articles.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        summary = response.choices[0].message.content
        
        # Add source links if not included by the AI
        if not any(item['url'] for item in news_items if item['url'] in summary):
            summary += "\n\nSources:\n"
            for item in news_items[:10]:
                summary += f"- {item['title']}: {item['url']}\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating news summary: {str(e)}")
        return "Sorry, I couldn't generate a summary at this time. Please try again later."
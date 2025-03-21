import re
import logging
import requests
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from openai import OpenAI
from config import OPENAI_API_KEY

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def extract_topics_from_news(news_item):
    """Extract relevant topics from a news item"""
    keywords = []
    # # Option 1: Simple keyword extraction
    # title = news_item.get('title', '').lower()
    
    # # AI-related keywords
    # ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'llm', 
    #               'gpt', 'deep learning', 'neural network']
    
    # # Funding-related keywords
    # funding_keywords = ['funding', 'investment', 'raises', 'venture', 'capital', 
    #                    'million', 'billion', 'series a', 'series b', 'seed']
    
    # # Technology domains
    # tech_domains = ['nlp', 'computer vision', 'robotics', 'generative ai', 
    #                'autonomous', 'cloud', 'saas']
    
    # # Check for keywords in title
    # for keyword in ai_keywords + funding_keywords + tech_domains:
    #     if keyword in title and keyword not in keywords:
    #         keywords.append(keyword)
    
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
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )

            logger.error(f"Extracted tags: {response}")
            
            ai_keywords = response.choices[0].message.content.split(',')
            ai_keywords = [k.strip().lower() for k in ai_keywords]
            
            # Add these to our keywords
            for k in ai_keywords:
                if k and k not in keywords:
                    keywords.append(k)
        except Exception as e:
            logger.error(f"Error using AI for keyword extraction: {e}")
    
    return keywords

def fetch_from_hackernews():
    """Fetch AI funding news from HackerNews API"""
    logger.info("Fetching news from HackerNews")
    
    try:
        response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        if response.status_code != 200:
            logger.error(f"HackerNews API returned status code {response.status_code}")
            return []
            
        # Get more stories to increase chances of finding AI funding news
        story_ids = response.json()[:100]  # Get top 100 stories
        logger.info(f"Retrieved {len(story_ids)} story IDs from HackerNews")
        
        stories = []
        ai_funding_count = 0
        
        for story_id in story_ids:
            if ai_funding_count >= 20:  # Stop once we have enough AI funding stories
                break
                
            try:
                story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                if story_response.status_code != 200:
                    continue
                    
                story = story_response.json()
                
                # Skip stories without a title or URL
                if not story.get('title') or not story.get('url'):
                    continue
                
                title = story.get('title', '').lower()
                
                # Check if it's about AI and funding
                ai_terms = ['ai', 'artificial intelligence', 'machine learning', 'neural', 'gpt', 'llm']
                funding_terms = ['fund', 'invest', 'capital', 'raise', 'million', 'billion', 'acquisition']
                
                is_ai_related = any(term in title for term in ai_terms)
                is_funding_related = any(term in title for term in funding_terms)
                
                # If it's clearly about AI funding, add it
                if is_ai_related and is_funding_related:
                    ai_funding_count += 1
                    logger.info(f"Found AI funding story: {story.get('title')}")
                # Or if it's just about AI, still add it but don't count it as an AI funding story
                elif is_ai_related:
                    logger.info(f"Found AI-related story: {story.get('title')}")
                else:
                    # Skip non-AI stories
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
                logger.error(f"Error processing HackerNews story: {e}")
        
        logger.info(f"Found {len(stories)} relevant stories from HackerNews")
        return stories
        
    except Exception as e:
        logger.error(f"Error fetching from HackerNews: {e}")
        return []

def fetch_from_techcrunch():
    """Fetch news from TechCrunch RSS feed"""
    logger.info("Fetching news from TechCrunch")
    
    try:
        response = requests.get("https://techcrunch.com/feed/")
        if response.status_code != 200:
            logger.error(f"TechCrunch RSS returned status code {response.status_code}")
            return []
        
        # Parse XML
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        logger.info(f"Retrieved {len(items)} items from TechCrunch RSS")
        
        stories = []
        for item in items:
            try:
                title = item.title.text
                
                # Check if it's about AI
                ai_terms = ['ai', 'artificial intelligence', 'machine learning', 'neural', 'gpt', 'llm']
                
                if any(term in title.lower() for term in ai_terms):
                    # Extract date
                    pub_date = item.pubDate.text
                    date_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                    date = date_obj.strftime('%Y-%m-%d')
                    
                    stories.append({
                        'title': title,
                        'url': item.link.text,
                        'date': date,
                        'source': 'TechCrunch'
                    })
                    logger.info(f"Found AI-related story: {title}")
            except Exception as e:
                logger.error(f"Error processing TechCrunch item: {e}")
        
        logger.info(f"Found {len(stories)} relevant stories from TechCrunch")
        return stories
        
    except Exception as e:
        logger.error(f"Error fetching from TechCrunch: {e}")
        return []

def filter_by_keywords(news_items):
    """Filter news items based on AI and funding keywords - more lenient to ensure we get enough stories"""
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'llm', 
                  'gpt', 'chatgpt', 'deep learning', 'neural network']
                  
    funding_keywords = ['funding', 'investment', 'raises', 'venture', 'capital', 'million', 
                       'billion', 'series a', 'series b', 'seed round']
    
    filtered_items = []
    
    for item in news_items:
        title = item.get('title', '').lower()
        
        # Check if it contains AI keywords
        has_ai = any(keyword in title for keyword in ai_keywords)
        
        # If it's AI-related, include it
        if has_ai:
            filtered_items.append(item)
            
            # Check if it also has funding keywords
            has_funding = any(keyword in title for keyword in funding_keywords)
            if has_funding:
                logger.info(f"AI funding article found: {item.get('title')}")
            else:
                logger.info(f"AI-related article found: {item.get('title')}")
    
    logger.info(f"Filtered to {len(filtered_items)} AI-related items from {len(news_items)} total")
    return filtered_items

def help_command(update, context):
    """Show enhanced help information"""
    help_text = (
        "🤖 *AI Funding News Bot* 🤖\n\n"
        "Get personalized AI funding and investment news with AI-powered insights.\n\n"
        "*Available Commands:*\n"
        "/start - Initialize the bot and set up preferences\n"
        "/news - Get personalized AI funding news with summaries\n"
        "/digest - Generate a comprehensive digest of recent AI funding news\n"
        "/interests - View your current interest topics\n"
        "/add\\_tag TAG \\[weight\\] - Add a new interest (e.g., /add\\_tag computer\\_vision 0.9)\n"
        "/remove\\_tag TAG - Remove an interest (e.g., /remove\\_tag blockchain)\n"
        "/adjust\\_interest TAG WEIGHT - Change priority of an interest\n"
        "/history - View your recently read news\n"
        "/clear\\_history - Clear your news history\n"
        "/reset - Reset your preferences and start over\n"
        "/help - Show this help message\n\n"
        "The bot uses AI to analyze news articles, provide summaries relevant to your interests, and generate insights tailored to your professional role."
    )
    
    try:
        update.message.reply_text(help_text, parse_mode='MarkdownV2')
    except Exception as e:
        # Fallback to plain text if Markdown fails
        fallback_text = (
            "🤖 AI Funding News Bot 🤖\n\n"
            "Get personalized AI funding and investment news with AI-powered insights.\n\n"
            "Available Commands:\n"
            "/start - Initialize the bot and set up preferences\n"
            "/news - Get personalized AI funding news with summaries\n"
            "/digest - Generate a comprehensive digest of recent AI funding news\n"
            "/interests - View your current interest topics\n"
            "/add_tag TAG [weight] - Add a new interest\n"
            "/remove_tag TAG - Remove an interest\n"
            "/adjust_interest TAG WEIGHT - Change priority of an interest\n"
            "/history - View your recently read news\n"
            "/clear_history - Clear your news history\n"
            "/reset - Reset your preferences and start over\n"
            "/help - Show this help message\n\n"
            "The bot uses AI to analyze news articles, provide summaries relevant to your interests, and generate insights tailored to your professional role."
        )
        update.message.reply_text(fallback_text)
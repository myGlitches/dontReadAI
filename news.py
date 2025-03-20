import requests
import logging
import json
from datetime import datetime, timedelta
import time
import random
from bs4 import BeautifulSoup
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_ai_tech_news(user_preferences=None):
    """Fetch AI funding news from multiple sources"""
    # Define keywords for filtering
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'llm', 
                  'gpt', 'chatgpt', 'openai', 'anthropic', 'claude', 'deep learning']
                  
    funding_keywords = ['funding', 'investment', 'raises', 'venture', 'capital', 'million', 
                       'billion', 'series a', 'series b', 'seed round', 'vc', 'investor']
    
    # Initialize list to store all stories
    all_stories = []
    
    # 1. Fetch from HackerNews
    hn_stories = fetch_from_hackernews(ai_keywords, funding_keywords)
    all_stories.extend(hn_stories)
    
    # 2. Fetch from TechCrunch via RSS
    tc_stories = fetch_from_techcrunch(ai_keywords, funding_keywords)
    all_stories.extend(tc_stories)
    
    # 3. Fetch from VentureBeat
    vb_stories = fetch_from_venturebeat(ai_keywords, funding_keywords)
    all_stories.extend(vb_stories)
    
    # 4. Fetch from Crunchbase News (funding focused)
    cb_stories = fetch_from_crunchbase(ai_keywords, funding_keywords)
    all_stories.extend(cb_stories)
    
    # Sort all stories by relevance and then by score/date
    sorted_stories = sorted(all_stories, key=lambda x: (x.get('relevance', 0), x.get('score', 0)), reverse=True)
    
    # If no stories found, log a message
    if not sorted_stories:
        logger.info("No AI funding stories found across any sources")
        
    return sorted_stories[:10]  # Return top 10 stories

def fetch_from_hackernews(ai_keywords, funding_keywords):
    """Fetch AI funding news from HackerNews API"""
    try:
        logger.info("Fetching from HackerNews...")
        response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        if response.status_code != 200:
            logger.error(f"HackerNews API error: {response.status_code}")
            return []
            
        story_ids = response.json()[:50]  # Get top 50 stories
        
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
                
                title = story.get('title', '').lower()
                text = story.get('text', '').lower() if story.get('text') else ''
                content = title + " " + text
                
                # Check if it's both AI and funding related
                is_ai_related = any(keyword in content for keyword in ai_keywords)
                is_funding_related = any(keyword in content for keyword in funding_keywords)
                
                if is_ai_related and is_funding_related:
                    # Calculate relevance score
                    relevance_score = 1.0
                    
                    # Give extra points for funding terms in the title
                    for keyword in funding_keywords:
                        if keyword in title:
                            relevance_score += 0.5
                    
                    # Give extra points for AI terms in the title
                    for keyword in ai_keywords:
                        if keyword in title:
                            relevance_score += 0.3
                    
                    timestamp = story.get('time', 0)
                    date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                    
                    stories.append({
                        'title': story.get('title'),
                        'url': story.get('url'),
                        'score': story.get('score', 0),
                        'date': date,
                        'source': 'HackerNews',
                        'relevance': relevance_score
                    })
                
                # Add a small delay to avoid hitting API limits
                time.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Error processing HackerNews story {story_id}: {str(e)}")
                continue
        
        logger.info(f"Found {len(stories)} matching stories from HackerNews")
        return stories
    except Exception as e:
        logger.error(f"Error fetching from HackerNews: {str(e)}")
        return []

def fetch_from_techcrunch(ai_keywords, funding_keywords):
    """Fetch AI funding news from TechCrunch RSS feed"""
    try:
        logger.info("Fetching from TechCrunch...")
        response = requests.get("https://techcrunch.com/feed/")
        if response.status_code != 200:
            logger.error(f"TechCrunch RSS error: {response.status_code}")
            return []
        
        # Parse XML
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        stories = []
        for item in items:
            try:
                title = item.title.text.lower()
                description = item.description.text.lower()
                content = title + " " + description
                
                # Check if it's both AI and funding related
                is_ai_related = any(keyword in content for keyword in ai_keywords)
                is_funding_related = any(keyword in content for keyword in funding_keywords)
                
                if is_ai_related and is_funding_related:
                    # Calculate relevance score
                    relevance_score = 1.0
                    
                    # Give extra points for funding terms in the title
                    for keyword in funding_keywords:
                        if keyword in title:
                            relevance_score += 0.5
                    
                    # Give extra points for AI terms in the title
                    for keyword in ai_keywords:
                        if keyword in title:
                            relevance_score += 0.3
                    
                    # Extract date
                    pub_date = item.pubDate.text
                    date_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                    date = date_obj.strftime('%Y-%m-%d')
                    
                    stories.append({
                        'title': item.title.text,
                        'url': item.link.text,
                        'date': date,
                        'source': 'TechCrunch',
                        'score': 10, # Default score
                        'relevance': relevance_score
                    })
            except Exception as e:
                logger.error(f"Error processing TechCrunch item: {str(e)}")
                continue
        
        logger.info(f"Found {len(stories)} matching stories from TechCrunch")
        return stories
    except Exception as e:
        logger.error(f"Error fetching from TechCrunch: {str(e)}")
        return []

def fetch_from_venturebeat(ai_keywords, funding_keywords):
    """Fetch AI funding news from VentureBeat"""
    try:
        logger.info("Fetching from VentureBeat...")
        # Try to fetch from their RSS feed
        response = requests.get("https://venturebeat.com/feed/")
        if response.status_code != 200:
            logger.error(f"VentureBeat RSS error: {response.status_code}")
            return []
        
        # Parse XML
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        stories = []
        for item in items:
            try:
                title = item.title.text.lower()
                description = item.description.text.lower()
                content = title + " " + description
                
                # Check if it's both AI and funding related
                is_ai_related = any(keyword in content for keyword in ai_keywords)
                is_funding_related = any(keyword in content for keyword in funding_keywords)
                
                if is_ai_related and is_funding_related:
                    # Calculate relevance score
                    relevance_score = 1.0
                    
                    # Give extra points for funding terms in the title
                    for keyword in funding_keywords:
                        if keyword in title:
                            relevance_score += 0.5
                    
                    # Give extra points for AI terms in the title
                    for keyword in ai_keywords:
                        if keyword in title:
                            relevance_score += 0.3
                    
                    # Extract date
                    pub_date = item.pubDate.text
                    date_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                    date = date_obj.strftime('%Y-%m-%d')
                    
                    stories.append({
                        'title': item.title.text,
                        'url': item.link.text,
                        'date': date,
                        'source': 'VentureBeat',
                        'score': 8,  # Default score
                        'relevance': relevance_score
                    })
            except Exception as e:
                logger.error(f"Error processing VentureBeat item: {str(e)}")
                continue
        
        logger.info(f"Found {len(stories)} matching stories from VentureBeat")
        return stories
    except Exception as e:
        logger.error(f"Error fetching from VentureBeat: {str(e)}")
        return []

def fetch_from_crunchbase(ai_keywords, funding_keywords):
    """Fetch AI funding news from Crunchbase News"""
    try:
        logger.info("Fetching from Crunchbase News...")
        # This would normally fetch from Crunchbase API, but it requires authentication
        # Instead, we'll use their RSS feed or recent funding page
        
        response = requests.get("https://news.crunchbase.com/feed/")
        if response.status_code != 200:
            logger.error(f"Crunchbase News RSS error: {response.status_code}")
            return []
        
        # Parse XML
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        stories = []
        for item in items:
            try:
                title = item.title.text.lower()
                description = item.description.text.lower() if item.description else ""
                content = title + " " + description
                
                # For Crunchbase, we prioritize AI keywords since it's already funding-focused
                is_ai_related = any(keyword in content for keyword in ai_keywords)
                
                if is_ai_related:
                    # Calculate relevance score - higher base score since it's Crunchbase (funding focused)
                    relevance_score = 1.2
                    
                    # Give extra points for AI terms in the title
                    for keyword in ai_keywords:
                        if keyword in title:
                            relevance_score += 0.4
                    
                    # Extract date if available
                    pub_date = item.pubDate.text if item.pubDate else None
                    if pub_date:
                        try:
                            date_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                            date = date_obj.strftime('%Y-%m-%d')
                        except:
                            date = datetime.now().strftime('%Y-%m-%d')
                    else:
                        date = datetime.now().strftime('%Y-%m-%d')
                    
                    stories.append({
                        'title': item.title.text,
                        'url': item.link.text,
                        'date': date,
                        'source': 'Crunchbase News',
                        'score': 12,  # Higher default score for Crunchbase (funding focused)
                        'relevance': relevance_score
                    })
            except Exception as e:
                logger.error(f"Error processing Crunchbase item: {str(e)}")
                continue
        
        logger.info(f"Found {len(stories)} matching stories from Crunchbase News")
        return stories
    except Exception as e:
        logger.error(f"Error fetching from Crunchbase News: {str(e)}")
        return []
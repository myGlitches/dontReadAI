# /news.py
import requests
import logging
import json
from datetime import datetime, timedelta
import time
from bs4 import BeautifulSoup
from openai import OpenAI
from config import OPENAI_API_KEY
from ai_analysis import analyze_news_relevance

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_ai_tech_news(user_preferences=None):
    """Fetch AI funding news from multiple sources, with AI ranking and recency filtering"""
    # Define keywords for filtering
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'llm', 
                  'gpt', 'chatgpt', 'openai', 'anthropic', 'claude', 'deep learning']
                  
    funding_keywords = ['funding', 'investment', 'raises', 'venture', 'capital', 'million', 
                       'billion', 'series a', 'series b', 'seed round', 'vc', 'investor']
                       
    # Keywords to exclude (like general acquisitions, mergers, etc.)
    exclude_keywords = ['acquisition', 'acquires', 'merger', 'merges with', 'buys', 'purchased']
    
    # Initialize list to store all stories
    all_stories = []
    
    # 1. Fetch from HackerNews
    hn_stories = fetch_from_hackernews(ai_keywords, funding_keywords, exclude_keywords)
    all_stories.extend(hn_stories)
    
    # 2. Fetch from TechCrunch via RSS
    tc_stories = fetch_from_techcrunch(ai_keywords, funding_keywords, exclude_keywords)
    all_stories.extend(tc_stories)
    
    # 3. Fetch from VentureBeat
    vb_stories = fetch_from_venturebeat(ai_keywords, funding_keywords, exclude_keywords)
    all_stories.extend(vb_stories)
    
    # 4. Fetch from Crunchbase News (funding focused)
    cb_stories = fetch_from_crunchbase(ai_keywords, funding_keywords, exclude_keywords)
    all_stories.extend(cb_stories)
    
    # If no stories found, return empty list
    if not all_stories:
        logger.info("No AI funding stories found from any source")
        return []
    
    # Filter for recency - only stories from the last few days
    today = datetime.now().date()
    recent_stories = []
    
    # Get recency preference (default 2 days)
    recency_days = 2
    if user_preferences and "recency_preference" in user_preferences:
        recency_days = user_preferences.get("recency_preference", 2)
    
    for story in all_stories:
        try:
            story_date = datetime.strptime(story['date'], '%Y-%m-%d').date()
            days_old = (today - story_date).days
            
            if days_old <= recency_days:  # Only include stories up to preference days old
                # Add days_old to the story data
                story['days_old'] = days_old
                recent_stories.append(story)
        except Exception as e:
            logger.error(f"Error parsing date for story {story.get('title', 'Unknown')}: {str(e)}")
    
    # If no recent stories, log and return empty list
    if not recent_stories:
        logger.info(f"No recent AI funding stories found within the last {recency_days} days")
        # Fall back to the 5 most recent stories regardless of date
        sorted_by_date = sorted(all_stories, 
                           key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d').date() 
                           if 'date' in x else datetime.now().date(), 
                           reverse=True)
        return sorted_by_date[:5]
    
    # If we have user preferences, do deep content analysis
    if user_preferences:
        logger.info("Performing deep content analysis on stories")
        deeply_filtered_stories = []
        
        # Only analyze top 10 stories to save API calls
        for story in recent_stories[:10]:
            try:
                # Perform deep content analysis
                analysis = analyze_news_relevance(story, user_preferences)
                relevance_score = analysis.get("relevance_score", 0)
                
                # Only include stories with relevance score of 6 or higher
                if relevance_score >= 6:
                    story['ai_relevance_score'] = relevance_score
                    story['ai_explanation'] = analysis.get("explanation", "")
                    deeply_filtered_stories.append(story)
                    logger.info(f"Story passed deep filtering: {story['title']} (Score: {relevance_score})")
                else:
                    logger.info(f"Story rejected by deep filtering: {story['title']} (Score: {relevance_score})")
            except Exception as e:
                logger.error(f"Error in deep content analysis: {str(e)}")
                # Include the story anyway if analysis fails
                recent_stories.append(story)
        
        # If we have deeply filtered stories, rank and return them
        if deeply_filtered_stories:
            logger.info(f"Ranking {len(deeply_filtered_stories)} stories that passed deep filtering")
            ranked_stories = ai_rank_stories(deeply_filtered_stories, user_preferences)
            return ranked_stories[:5]
    
    # If deep filtering didn't yield results or there are no user preferences, 
    # fall back to basic ranking
    logger.info(f"Using basic ranking for {len(recent_stories)} recent stories")
    ranked_stories = ai_rank_stories(recent_stories, user_preferences)
    return ranked_stories[:5]

def ai_rank_stories(stories, user_preferences):
    """Use AI to rank stories based on relevance, recency, and user preferences"""
    try:
        # Default to general investor if no preferences
        if not user_preferences:
            user_preferences = {
                "role": "investor",
                "interests": {"ai_funding": 1.0},
                "technical_level": "intermediate"
            }
        
        # Extract user role and interests for the AI
        user_role = user_preferences.get("role", "investor")
        
        # Handle case where interests might not be a dictionary
        interests_dict = user_preferences.get("interests", {})
        if not isinstance(interests_dict, dict) or not interests_dict:
            interests_dict = {"ai_funding": 1.0}
        
        user_interests = list(interests_dict.keys())
        technical_level = user_preferences.get("technical_level", "intermediate")
        
        # Create a condensed summary of stories to avoid token limits
        story_summaries = []
        for i, story in enumerate(stories):
            summary = {
                "id": i,
                "title": story.get("title", ""),
                "source": story.get("source", ""),
                "days_old": story.get("days_old", 0)
            }
            story_summaries.append(summary)
        
        # Guard against empty lists
        if not story_summaries:
            logger.warning("No stories to rank with AI")
            return stories
        
        # Create safe string for interests that won't cause format errors
        interests_str = ""
        try:
            interests_str = ', '.join(user_interests)
        except Exception as e:
            logger.error(f"Error joining interests: {e}")
            interests_str = "AI funding"
        
        # Create the prompt for AI ranking with safe string formatting
        prompt = """
        You are an AI news curator specializing in AI funding and investment news.
        
        USER PROFILE:
        - Role: {}
        - Technical level: {}
        - Interests: {}
        
        TASK:
        Rank the following AI funding news stories based on:
        1. Relevance to AI funding/investment
        2. Recency (newer is better)
        3. Relevance to the user's interests and role
        4. Importance in the AI ecosystem
        
        NEWS STORIES:
        {}
        
        Return a JSON array of story IDs in ranked order (best first), with a 1-sentence explanation for each ranking:
        [
          {{"id": story_id, "explanation": "Brief reason for ranking"}},
          ...
        ]
        
        Only include stories truly relevant to AI funding and investment.
        """.format(user_role, technical_level, interests_str, json.dumps(story_summaries, indent=2))
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI news curator specializing in AI funding."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        # Parse the AI's ranking
        try:
            ranking_data = json.loads(response.choices[0].message.content)
            
            # Check if the response has the expected format
            if not isinstance(ranking_data, list):
                logger.error("AI ranking response is not a list")
                return stories
                
            ranked_ids = []
            for item in ranking_data:
                if isinstance(item, dict) and "id" in item:
                    ranked_ids.append(item["id"])
            
            # Reorder stories based on AI ranking
            ranked_stories = []
            for story_id in ranked_ids:
                if story_id < len(stories):
                    story = stories[story_id]
                    # Add the AI's explanation to the story
                    matching_items = [item for item in ranking_data if item.get("id") == story_id]
                    if matching_items:
                        story["ai_explanation"] = matching_items[0].get("explanation", "Relevant AI funding news")
                    ranked_stories.append(story)
            
            # Add any stories that weren't ranked at the end
            for i, story in enumerate(stories):
                if i not in ranked_ids:
                    ranked_stories.append(story)
                    
            logger.info(f"Successfully ranked {len(ranked_stories)} stories with AI")
            return ranked_stories
            
        except Exception as e:
            logger.error(f"Error parsing AI ranking response: {str(e)}")
            # Fall back to simple sorting by date and relevance
            return sorted(stories, key=lambda x: (x.get('days_old', 999), -x.get('relevance', 0)))
            
    except Exception as e:
        logger.error(f"Error during AI ranking: {str(e)}")
        # Fall back to simple sorting by date and relevance
        return sorted(stories, key=lambda x: (x.get('days_old', 999), -x.get('relevance', 0)))

def fetch_from_hackernews(ai_keywords, funding_keywords, exclude_keywords):
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
                
                # Check if it contains any excluded terms (unless they also have funding terms)
                contains_excluded = any(keyword in content for keyword in exclude_keywords)
                # If it has excluded terms, make sure it has stronger funding signals
                if contains_excluded and not any(keyword in title for keyword in funding_keywords):
                    continue
                
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

def fetch_from_techcrunch(ai_keywords, funding_keywords, exclude_keywords):
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
                
                # Check if it contains any excluded terms (unless they also have funding terms)
                contains_excluded = any(keyword in content for keyword in exclude_keywords)
                # If it has excluded terms, make sure it has stronger funding signals
                if contains_excluded and not any(keyword in title for keyword in funding_keywords):
                    continue
                
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

def fetch_from_venturebeat(ai_keywords, funding_keywords, exclude_keywords):
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
                
                # Check if it contains any excluded terms (unless they also have funding terms)
                contains_excluded = any(keyword in content for keyword in exclude_keywords)
                # If it has excluded terms, make sure it has stronger funding signals
                if contains_excluded and not any(keyword in title for keyword in funding_keywords):
                    continue
                
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

def fetch_from_crunchbase(ai_keywords, funding_keywords, exclude_keywords):
    """Fetch AI funding news from Crunchbase News"""
    try:
        logger.info("Fetching from Crunchbase News...")
        
        # Add User-Agent header to avoid 403 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Try to fetch from their RSS feed
        response = requests.get("https://news.crunchbase.com/feed/", headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Crunchbase News RSS error: {response.status_code}")
            # Return empty list instead of failing
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
                
                # Check if it's both AI and funding related
                is_ai_related = any(keyword in content for keyword in ai_keywords)
                is_funding_related = any(keyword in content for keyword in funding_keywords)
                
                # Check if it contains any excluded terms (unless they also have funding terms)
                contains_excluded = any(keyword in content for keyword in exclude_keywords)
                # If it has excluded terms, make sure it has stronger funding signals in the title
                if contains_excluded and not any(keyword in title for keyword in funding_keywords):
                    continue
                
                # Must be both AI-related AND funding-related
                if is_ai_related and is_funding_related:
                    # Calculate relevance score - higher base score since it's Crunchbase
                    relevance_score = 1.2
                    
                    # Give extra points for AI terms in the title
                    for keyword in ai_keywords:
                        if keyword in title:
                            relevance_score += 0.3
                    
                    # Give extra points for funding terms in the title
                    for keyword in funding_keywords:
                        if keyword in title:
                            relevance_score += 0.5
                    
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
        # Return empty list instead of failing
        return []
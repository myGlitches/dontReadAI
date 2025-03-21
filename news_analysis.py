import logging
import requests
from bs4 import BeautifulSoup
import json
from openai import OpenAI
from config import OPENAI_API_KEY

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_article_content(url):
    """Fetch the full content of a news article"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AINewsBot/1.0)'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove noise elements
        for element in soup.select('nav, header, footer, aside, script, style, .ads, .comments'):
            element.extract()
        
        # Try to find main article content
        content_selectors = [
            'article', '.article-content', '.entry-content', '.post-content',
            '.article-body', 'main', '#content', '.story'
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content and len(content.get_text(strip=True)) > 300:
                return clean_content(content.get_text(strip=True))
        
        # Fallback to body content
        body_text = soup.body.get_text(strip=True)
        return clean_content(body_text)
    
    except Exception as e:
        logger.error(f"Error fetching article content: {str(e)}")
        return ""

def clean_content(text):
    """Clean and normalize extracted content"""
    # Remove excessive whitespace
    text = ' '.join(text.split())
    return text

def analyze_news_relevance(news_item, user_preferences, include_summary=True):
    """
    Enhanced version that analyzes article content for relevance and 
    generates a personalized summary
    """
    # First, try to fetch full article content
    article_content = ""
    if "url" in news_item:
        article_content = fetch_article_content(news_item.get("url", ""))
    
    # Extract user interests and role
    interests = user_preferences.get("interests", {})
    user_role = user_preferences.get("role", "investor")
    technical_level = user_preferences.get("technical_level", "intermediate")
    
    # Create prompt for relevance analysis
    prompt = f"""
    Analyze this AI funding news item's relevance to a user with the following profile:
    
    USER PROFILE:
    - Role: {user_role}
    - Interests: {", ".join(interests.keys())}
    - Technical expertise: {technical_level}
    
    NEWS ITEM:
    - Title: {news_item.get('title', '')}
    - Source: {news_item.get('source', '')}
    - Date: {news_item.get('date', '')}
    
    ARTICLE CONTENT:
    {article_content[:3000] if article_content else "Not available"}
    
    First, identify up to 5 key topics in this article.
    
    Then, on a scale of 1-10, rate how relevant this news item is to the user, where:
    - 10 = Extremely relevant, perfect match to interests and role
    - 7-9 = Very relevant, strong match to multiple interests
    - 4-6 = Moderately relevant, matches some interests
    - 1-3 = Low relevance, minimal connection to interests
    
    Also provide a one-sentence explanation of your rating.
    
    Respond in JSON format:
    {{
        "relevance_score": number,
        "explanation": "string",
        "topics": ["topic1", "topic2", "topic3"],
        "summary": "a concise summary focused on points relevant to the user's interests"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a personalized AI news recommendation and analysis engine."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        analysis = json.loads(response.choices[0].message.content)
        
        # If we don't need a summary (for bulk processing), we can remove it to save tokens
        if not include_summary and "summary" in analysis:
            del analysis["summary"]
            
        return analysis
    
    except Exception as e:
        logger.error(f"Error analyzing news relevance: {str(e)}")
        return {
            "relevance_score": 5,
            "explanation": "Unable to assess relevance due to an error.",
            "topics": [],
            "summary": f"Summary not available. Original title: {news_item.get('title', '')}"
        }

def generate_digest(news_items, user_preferences):
    """Generate a personalized news digest from multiple items"""
    # Extract user interests and role
    interests = user_preferences.get("interests", {})
    user_role = user_preferences.get("role", "investor")
    
    # Format the news items for the prompt
    formatted_items = []
    for item in news_items:
        formatted_items.append({
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "relevance_score": item.get("relevance_score", 5),
            "topics": item.get("topics", []),
            "summary": item.get("summary", "")
        })
    
    # Create prompt for digest generation
    prompt = f"""
    Create a concise AI funding news digest for a {user_role} interested in {", ".join(interests.keys())}.
    
    TODAY'S TOP AI FUNDING NEWS:
    {json.dumps(formatted_items, indent=2)}
    
    The digest should:
    1. Start with a brief overview of the key AI funding trends from these articles
    2. Highlight the most important developments that match the user's interests
    3. Include any actionable insights for someone in the user's role
    4. Keep the entire digest under 300 words
    
    Format the digest in a clean, readable style for a Telegram message.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a personalized AI news digest creator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        # Return the digest text
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"Error generating news digest: {str(e)}")
        return "Sorry, we couldn't generate your AI funding news digest at this time."
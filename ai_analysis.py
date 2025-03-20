# /ai_analysis.py
import json
import logging
from openai import OpenAI
from config import OPENAI_API_KEY

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def extract_interests_with_ai(user_text):
    """Use AI to extract interests and preferences from user text"""
    logger.info(f"Analyzing user interests with AI: {user_text[:50]}...")
    
    prompt = f"""
    Analyze the following text where a user describes their interest in AI news.
    Extract:
    1. Their likely role in the AI ecosystem (investor, founder, developer, researcher, executive, or general enthusiast)
    2. Key AI topics they're interested in (at least 3-5 specific topics)
    3. Their technical expertise level (beginner, intermediate, advanced)
    4. Their preferred news sources (if mentioned)
    5. What timeframe they're most interested in (today's news, weekly roundup, etc.)
    
    For the topics, be specific and focus on AI funding categories:
    - Specific AI domains (generative AI, computer vision, NLP, etc.)
    - Industry applications (healthcare AI, fintech AI, etc.)
    - Funding stages (seed, series A, growth)
    - Geographic regions (US, EU, APAC, etc.)
    
    User text: "{user_text}"
    
    Respond in JSON format:
    {{
        "role": "role_name",
        "topics": ["topic1", "topic2", "topic3", "topic4", "topic5"],
        "technical_level": "level",
        "preferred_sources": ["source1", "source2"],
        "time_preference": "preference",
        "focus_categories": ["category1", "category2"]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert analyst of VC and funding preferences in the AI ecosystem."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        ai_extracted = json.loads(response.choices[0].message.content)
        
        # Convert to weighted interests format
        interests = {}
        for topic in ai_extracted.get("topics", []):
            interests[topic] = 0.8  # Default high weight for extracted topics
        
        # Add focus categories with higher weights
        for category in ai_extracted.get("focus_categories", []):
            interests[category] = 1.0  # Higher weight for focus categories
        
        # Map technical level to content detail preference
        content_length_map = {
            "beginner": "simplified",
            "intermediate": "balanced",
            "advanced": "detailed"
        }
        
        # Process time preferences
        time_pref = ai_extracted.get("time_preference", "recent")
        recency_pref = 2  # Default to 2 days max
        if "weekly" in time_pref.lower():
            recency_pref = 7
        elif "month" in time_pref.lower():
            recency_pref = 30
        
        # Build final preferences structure
        result = {
            "role": ai_extracted.get("role", "investor"),
            "interests": interests,
            "preferred_sources": ai_extracted.get("preferred_sources", ["HackerNews", "TechCrunch"]),
            "content_length": content_length_map.get(ai_extracted.get("technical_level", "intermediate"), "balanced"),
            "technical_level": ai_extracted.get("technical_level", "intermediate"),
            "recency_preference": recency_pref
        }
        
        logger.info(f"Successfully extracted preferences: {result['role']}, {list(interests.keys())[:3]}")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting preferences with AI: {str(e)}")
        # Return default preferences if AI fails
        return {
            "role": "investor",
            "interests": {"AI funding": 1.0, "venture capital": 0.9, "startups": 0.8},
            "preferred_sources": ["HackerNews", "TechCrunch"],
            "content_length": "balanced",
            "technical_level": "intermediate",
            "recency_preference": 2
        }

def analyze_news_relevance(news_item, user_preferences):
    """Analyze how relevant a news item is to the user's preferences"""
    try:
        # Extract user interests and role
        interests = user_preferences.get("interests", {})
        user_role = user_preferences.get("role", "investor")
        
        # Create prompt for the AI
        prompt = f"""
        Analyze this AI funding news item's relevance to a user with the following profile:
        
        USER PROFILE:
        - Role: {user_role}
        - Interests: {", ".join(interests.keys())}
        
        NEWS ITEM:
        - Title: {news_item.get('title', '')}
        - Source: {news_item.get('source', '')}
        - Date: {news_item.get('date', '')}
        
        On a scale of 1-10, rate how relevant this news item is to the user, where:
        - 10 = Extremely relevant, perfect match to interests and role
        - 7-9 = Very relevant, strong match to multiple interests
        - 4-6 = Moderately relevant, matches some interests
        - 1-3 = Low relevance, minimal connection to interests
        
        Also provide a one-sentence explanation of your rating.
        
        Respond in JSON format:
        {{
            "relevance_score": number,
            "explanation": "string"
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a personalized AI news recommendation engine."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        analysis = json.loads(response.choices[0].message.content)
        
        return {
            "relevance_score": analysis.get("relevance_score", 5),
            "explanation": analysis.get("explanation", "")
        }
    
    except Exception as e:
        logger.error(f"Error analyzing news relevance: {str(e)}")
        return {
            "relevance_score": 5,
            "explanation": "Unable to assess relevance due to an error."
        }
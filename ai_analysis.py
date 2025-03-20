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
    1. Their likely role (developer, founder, investor, researcher, or general)
    2. Key AI topics they're interested in (at least 3-5 topics)
    3. Their technical level (beginner, intermediate, advanced)
    
    User text: "{user_text}"
    
    Respond in JSON format:
    {{
        "role": "role_name",
        "topics": ["topic1", "topic2", "topic3"],
        "technical_level": "level",
        "source_preference": ["preferred_sources"]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You analyze user preferences for an AI news service."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        preferences = json.loads(response.choices[0].message.content)
        
        # Convert to weights format
        interests = {}
        for topic in preferences["topics"]:
            interests[topic] = 0.8  # Default high weight for extracted topics
        
        # Map technical level to content detail preference
        content_length_map = {
            "beginner": "simplified",
            "intermediate": "balanced",
            "advanced": "detailed"
        }
        
        result = {
            "role": preferences["role"],
            "interests": interests,
            "preferred_sources": preferences.get("source_preference", ["ArXiv", "HackerNews"]),
            "content_length": content_length_map.get(preferences["technical_level"], "balanced"),
            "technical_level": preferences["technical_level"]
        }
        
        logger.info(f"Successfully extracted preferences: {result['role']}, {list(interests.keys())[:3]}")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting preferences with AI: {str(e)}")
        # Return default preferences if AI fails
        return {
            "role": "general",
            "interests": {"AI": 0.8, "technology": 0.7},
            "preferred_sources": ["HackerNews", "TechCrunch"],
            "content_length": "balanced",
            "technical_level": "intermediate"
        }
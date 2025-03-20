# /content.py
import openai
import logging
from config import OPENAI_API_KEY

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

def generate_social_post(news_item, platform, user_preferences):
    """Generate social media post using OpenAI based on user preferences"""
    
    # Log that we're starting content generation
    logger.info(f"Generating content for platform: {platform}, news item: {news_item['title']}")
    
    # Extract user preferences
    role = user_preferences.get('role', 'general')
    technical_level = user_preferences.get('technical_level', 'intermediate')
    content_length = user_preferences.get('content_length', 'balanced')
    
    # Build a personalized prompt
    platform_style = {
        "twitter": "brief, engaging, max 280 chars",
        "linkedin": "professional, insightful",
        "reddit": "conversational, detailed with a catchy title"
    }.get(platform.lower(), "concise, informative")
    
    prompt = f"""
    Create a {platform} post about this AI news: '{news_item['title']}'. 
    URL: {news_item['url']}
    
    Tailor this for a {role} with {technical_level} technical knowledge.
    Make it {platform_style} and {content_length} in detail.
    Include 2-3 relevant hashtags.
    """
    
    try:
        logger.info("Calling OpenAI API")
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant that creates engaging, personalized social media posts about AI news."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=350,
            temperature=0.7
        )
        generated_text = response.choices[0].message.content
        logger.info(f"Successfully generated content: {generated_text[:50]}...")
        
        return generated_text
    except Exception as e:
        error_msg = f"Error generating content: {str(e)}"
        logger.error(error_msg)
        return f"Sorry, I encountered an error creating your post. Here's the news link instead:\n{news_item['title']}\n{news_item.get('url', '')} #AI #Tech"
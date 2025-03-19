import openai
import logging
from config import OPENAI_API_KEY

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

def generate_social_post(news_item, platform, user_interest):
    """Generate social media post using OpenAI"""
    
    # Log that we're starting content generation
    logger.info(f"Generating content for platform: {platform}, news item: {news_item['title']}")
    
    platform_prompts = {
        "twitter": f"Create a Twitter post (max 280 chars) about this AI news: '{news_item['title']}'. Focus on {user_interest} aspects. Include 2-3 relevant hashtags.",
        "linkedin": f"Create a short LinkedIn post (under 400 chars) about this AI news: '{news_item['title']}'. Focus on {user_interest} aspects. Keep it professional but engaging.",
        "reddit": f"Create a Reddit post title and short body text about this AI news: '{news_item['title']}'. Focus on {user_interest} aspects. Make it suitable for an AI/tech subreddit."
    }
    
    prompt = platform_prompts.get(platform.lower(), platform_prompts["twitter"])
    
    try:
        logger.info("Calling OpenAI API")
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant that creates engaging, concise social media posts about AI news."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=350,
            temperature=0.7
        )
        generated_text = response.choices[0].message.content
        logger.info(f"Successfully generated content: {generated_text[:50]}...")
        
        # Always include the URL in the return
        return f"{generated_text}\n\nLink: {news_item.get('url', '')}"
    except Exception as e:
        error_msg = f"Error generating content: {str(e)}"
        logger.error(error_msg)
        return f"Sorry, I encountered an error creating your post. Here's the news link instead:\n{news_item['title']}\n{news_item.get('url', '')} #AI #Tech"
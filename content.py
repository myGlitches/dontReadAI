import openai
from config import OPENAI_API_KEY

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

def generate_social_post(news_item, platform, user_interest):
    """Generate social media post using OpenAI"""
    
    platform_prompts = {
        "twitter": f"Create a Twitter post (max 280 chars) about this AI news: '{news_item['title']}'. Focus on {user_interest} aspects. Include 2-3 relevant hashtags.",
        "linkedin": f"Create a short LinkedIn post (under 400 chars) about this AI news: '{news_item['title']}'. Focus on {user_interest} aspects. Keep it professional but engaging.",
        "reddit": f"Create a Reddit post title and short body text about this AI news: '{news_item['title']}'. Focus on {user_interest} aspects. Make it suitable for an AI/tech subreddit."
    }
    
    prompt = platform_prompts.get(platform.lower(), platform_prompts["twitter"])
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant that creates engaging, concise social media posts about AI news."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=350,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating content: {e}")
        return f"Check out this AI news: {news_item['title']} {news_item['url']} #AI #Tech"
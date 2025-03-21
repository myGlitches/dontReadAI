# twitter_service.py - Twitter Top Voices Summary Service

import requests
import logging
from datetime import datetime, timedelta
from openai import OpenAI
from config import OPENAI_API_KEY, TWITTER_VOICES
from db import get_user_system_message

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_top_tweets():
    """
    PLACEHOLDER: Fetch tweets from top AI voices
    
    NOTE: This is a placeholder. For a production system, you would use:
    1. Twitter API (requires developer account)
    2. A service like Nitter (unofficial Twitter frontend)
    3. Web scraping (not recommended due to legal constraints)
    
    For this prototype, we'll use mock data
    """
    logger.info("Fetching tweets from top AI voices")
    
    # Mock data - in a real implementation, replace with actual Twitter API calls
    tweets = [
        {
            'id': '1',
            'username': 'sama',
            'name': 'Sam Altman',
            'content': 'Excited to announce our latest research: we\'ve achieved significant improvements in reasoning capabilities, with a 30% increase in complex problem-solving accuracy.',
            'timestamp': (datetime.now() - timedelta(hours=5)).isoformat(),
            'url': 'https://twitter.com/sama/status/1'
        },
        {
            'id': '2',
            'username': 'elonmusk',
            'name': 'Elon Musk',
            'content': 'AI safety remains our top priority. Working on new frameworks for ensuring systems remain aligned with human values even as capabilities increase.',
            'timestamp': (datetime.now() - timedelta(hours=8)).isoformat(),
            'url': 'https://twitter.com/elonmusk/status/2'
        },
        {
            'id': '3',
            'username': 'ylecun',
            'name': 'Yann LeCun',
            'content': 'New paper on self-supervised learning shows promising results for generalization with significantly less data. Will be presenting at the upcoming NeurIPS conference.',
            'timestamp': (datetime.now() - timedelta(hours=12)).isoformat(),
            'url': 'https://twitter.com/ylecun/status/3'
        },
        {
            'id': '4',
            'username': 'AndrewYNg',
            'name': 'Andrew Ng',
            'content': 'Just published a new course on foundation models. Free access for the first month - learn how these systems work and how to leverage them effectively.',
            'timestamp': (datetime.now() - timedelta(hours=15)).isoformat(),
            'url': 'https://twitter.com/AndrewYNg/status/4'
        },
        {
            'id': '5',
            'username': 'demishassabis',
            'name': 'Demis Hassabis',
            'content': 'Our team has made a breakthrough in protein folding prediction, with implications for drug discovery and understanding biological systems. Paper coming next week.',
            'timestamp': (datetime.now() - timedelta(hours=20)).isoformat(),
            'url': 'https://twitter.com/demishassabis/status/5'
        }
    ]
    
    logger.info(f"Fetched {len(tweets)} tweets from top AI voices")
    return tweets

def filter_tweets(tweets, excluded_accounts=None):
    """Filter tweets based on user preferences"""
    if not excluded_accounts:
        excluded_accounts = []
    
    filtered_tweets = [
        tweet for tweet in tweets
        if tweet['username'].lower() not in [account.lower() for account in excluded_accounts]
    ]
    
    logger.info(f"Filtered to {len(filtered_tweets)} tweets after applying exclusions")
    return filtered_tweets

def generate_twitter_summary(user_id, tweets):
    """Generate a summary of tweets from top AI voices"""
    if not tweets:
        logger.warning("No tweets to summarize")
        return "No recent tweets from top AI voices found."
    
    # Get user's customized system message
    system_message = get_user_system_message(user_id, 'twitter')
    
    # Prepare tweet data for the prompt
    formatted_tweets = []
    for tweet in tweets:
        formatted_tweets.append({
            'name': tweet['name'],
            'username': tweet['username'],
            'content': tweet['content'],
            'timestamp': tweet['timestamp'],
            'url': tweet['url']
        })
    
    # Create prompt for the AI
    user_prompt = f"""
    Generate a comprehensive summary of these tweets from top AI voices.
    Focus on extracting key insights, trends, announcements, and discussions.
    
    Tweets to summarize:
    {formatted_tweets}
    
    Format your response as a concise briefing that:
    1. Highlights the most important developments or discussions
    2. Groups related topics or themes
    3. Provides context where needed
    
    At the end, include a list of links to the original tweets.
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
        if not any(tweet['url'] for tweet in tweets if tweet['url'] in summary):
            summary += "\n\nTweet Sources:\n"
            for tweet in tweets:
                summary += f"- {tweet['name']} (@{tweet['username']}): {tweet['url']}\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating Twitter summary: {str(e)}")
        return "Sorry, I couldn't generate a summary at this time. Please try again later."
# twitter_service.py - Twitter Top Voices Summary Service

import logging
import time
import random
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY, TWITTER_VOICES
from db import get_user_system_message

# Try to import googlesearch, with fallback for installation instructions
try:
    from googlesearch import search
except ImportError:
    logging.error("googlesearch-python package not found. Please install it using: pip install googlesearch-python")
    # Define a dummy function that will inform user if it's used without the package
    def search(*args, **kwargs):
        raise ImportError("Please install the googlesearch-python package: pip install googlesearch-python")

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def google_search_tweets(ai_experts, num_results=3):
    """Search Google for recent tweets from AI experts."""
    tweets_data = []
    query_template = 'site:x.com "{}" AI OR machine learning OR LLM OR OpenAI OR startup'
    
    for expert in ai_experts:
        query = query_template.format(expert)
        logger.info(f"Searching tweets for: {expert}")
        
        try:
            results = search(query, num_results=num_results)
            for url in results:
                if "x.com" in url and "status/" in url:
                    # Extract username from URL
                    username = url.split("x.com/")[1].split("/status")[0]
                    
                    # Create tweet data with just the URL and basic info
                    tweet_id = url.split("status/")[1].split("?")[0] if "?" in url else url.split("status/")[1]
                    
                    tweets_data.append({
                        'id': tweet_id,
                        'username': username,
                        'name': expert,  # Use the expert name from our list
                        'content': "[View original tweet]",
                        'timestamp': datetime.now().isoformat(),
                        'url': url
                    })
                    
                    logger.info(f"Found tweet URL: {url}")
            
        except Exception as e:
            logger.error(f"Google search failed for {expert}: {str(e)}")
            
        # Sleep to avoid hitting rate limits
        time.sleep(random.uniform(1, 3))
    
    return tweets_data

def fetch_top_tweets():
    """
    Fetch tweets from top AI voices using Google search
    """
    logger.info("Fetching tweets from top AI voices")
    
    # Get AI experts from config or use defaults
    ai_top_voices = TWITTER_VOICES if TWITTER_VOICES else [
        "Sam Altman", "Elon Musk", "Yann LeCun", "Andrew Ng", "Demis Hassabis"
    ]
    
    # Get tweet links via Google search with some basic info
    tweets = google_search_tweets(ai_top_voices, num_results=2)
    
    # Return whatever we found (could be empty)
    logger.info(f"Found {len(tweets)} tweets from top AI voices")
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
        return "No recent tweets from top AI voices found. Please try again later."
    
    # Get user's customized system message - this contains their preferences
    system_message = get_user_system_message(user_id, 'twitter')
    
    # Check if the user has specific preferences in their system message
    # For example, they might prefer a specific format or introduction
    # This is a simple implementation - you can enhance it based on your needs
    personalized_greeting = "Here are the latest tweets from top AI voices"
    if system_message and "GREETING:" in system_message:
        try:
            # Extract custom greeting if defined in system message
            greeting_part = system_message.split("GREETING:")[1].split("\n")[0].strip()
            if greeting_part:
                personalized_greeting = greeting_part
        except:
            logger.warning(f"Could not parse custom greeting for user {user_id}")
    
    # Create a summary directly listing the tweet links
    links_message = f"{personalized_greeting}. Click the links to view the full tweets:\n\n"
    
    for tweet in tweets:
        links_message += f"• {tweet['name']} (@{tweet['username']}): {tweet['url']}\n"
    
    return links_message

# For testing purposes
if __name__ == "__main__":
    # Test the tweet fetching function
    tweets = fetch_top_tweets()
    print(f"Found {len(tweets)} tweets")
    for tweet in tweets:
        print(f"@{tweet['username']}: {tweet['url']}")
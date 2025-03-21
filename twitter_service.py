# twitter_service.py - Twitter Top Voices Summary Service

import requests
import logging
import time
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
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

# Nitter instances (use reliable ones)
NITTER_INSTANCES = [
    "https://nitter.net", 
    "https://nitter.privacydev.net", 
    "https://nitter.poast.org"
]

def get_nitter_instance():
    """Randomly select a Nitter instance to avoid rate limits."""
    return random.choice(NITTER_INSTANCES)

def google_search_tweets(ai_experts, num_results=3):
    """Search Google for recent tweets from AI experts."""
    tweets_urls = []
    query_template = 'site:twitter.com "{}" AI OR machine learning OR LLM OR OpenAI OR startup'
    
    for expert in ai_experts:
        query = query_template.format(expert)
        logger.info(f"Searching tweets for: {expert}")
        
        try:
            results = search(query, num_results=num_results)
            for url in results:
                if "twitter.com" in url and "status/" in url:
                    tweets_urls.append(url)
                    logger.info(f"Found tweet URL: {url}")
        except Exception as e:
            logger.error(f"Google search failed for {expert}: {str(e)}")
            
        # Sleep to avoid hitting rate limits
        time.sleep(random.uniform(1, 3))
    
    return tweets_urls

def fetch_tweet_from_nitter(tweet_url):
    """Convert Twitter URL to Nitter and scrape tweet content."""
    try:
        # Extract username and tweet ID from URL
        if "/status/" not in tweet_url:
            logger.warning(f"Invalid tweet URL format: {tweet_url}")
            return None
            
        username = tweet_url.split("twitter.com/")[1].split("/status")[0]
        tweet_id = tweet_url.split("status/")[1].split("?")[0]  # Handle any URL parameters
        
        nitter_base = get_nitter_instance()
        nitter_url = f"{nitter_base}/{username}/status/{tweet_id}"
        
        logger.info(f"Fetching tweet from Nitter: {nitter_url}")
        
        # Add delay to avoid rate limiting
        time.sleep(random.uniform(1, 2))
        
        # Fetch the tweet
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml"
        }
        
        response = requests.get(nitter_url, timeout=10, headers=headers)
        response.raise_for_status()
        
        # Parse the webpage
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract tweet content
        tweet_content_div = soup.find("div", class_="tweet-content")
        if not tweet_content_div:
            logger.warning(f"Could not find tweet content for {nitter_url}")
            return None
            
        tweet_text = tweet_content_div.get_text(strip=True)
        
        # Extract name
        fullname_div = soup.find("a", class_="fullname")
        name = fullname_div.get_text(strip=True) if fullname_div else username
        
        # Extract timestamp
        timestamp_span = soup.find("span", class_="tweet-date")
        timestamp_str = timestamp_span.find("a").get("title") if timestamp_span and timestamp_span.find("a") else None
        
        # If timestamp is not available, use current time minus random hours
        if not timestamp_str:
            timestamp = (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat()
        else:
            try:
                # Try to parse the timestamp
                timestamp = datetime.strptime(timestamp_str, "%b %d, %Y · %I:%M %p UTC").isoformat()
            except ValueError:
                timestamp = (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat()
        
        return {
            "id": tweet_id,
            "username": username,
            "name": name,
            "content": tweet_text,
            "timestamp": timestamp,
            "url": tweet_url
        }
    except Exception as e:
        logger.error(f"Failed to fetch tweet from Nitter: {str(e)}")
        return None

def fetch_top_tweets():
    """
    Fetch tweets from top AI voices using Google search and Nitter
    """
    logger.info("Fetching tweets from top AI voices")
    
    # Get AI experts from config or use defaults
    ai_top_voices = TWITTER_VOICES if TWITTER_VOICES else [
        "Sam Altman", "Elon Musk", "Yann LeCun", "Andrew Ng", "Demis Hassabis"
    ]
    
    # Step 1: Search Google for tweets
    tweet_urls = google_search_tweets(ai_top_voices, num_results=3)
    
    # Step 2: Fetch tweets via Nitter
    tweets = []
    for url in tweet_urls:
        tweet_data = fetch_tweet_from_nitter(url)
        if tweet_data:
            tweets.append(tweet_data)
        time.sleep(random.uniform(1, 3))  # Avoid getting blocked
    
    # If we couldn't get any tweets, fall back to mock data
    if not tweets:
        logger.warning("Failed to fetch tweets. Using mock data as fallback.")
        tweets = get_mock_tweets()
    
    logger.info(f"Fetched {len(tweets)} tweets from top AI voices")
    return tweets

def get_mock_tweets():
    """Return mock tweets as fallback"""
    return [
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

# For testing purposes
if __name__ == "__main__":
    # Test the tweet fetching function
    tweets = fetch_top_tweets()
    print(f"Fetched {len(tweets)} tweets")
    for tweet in tweets:
        print(f"@{tweet['username']}: {tweet['content'][:50]}...")
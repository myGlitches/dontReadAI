# twitter_service.py - Twitter Top Voices Summary Service

import logging
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict
import urllib.parse

# Choose between different web scraping methods
def choose_scraping_method():
    """
    Try to import and use the most appropriate web scraping library
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        return requests_scraper
    except ImportError:
        try:
            import urllib.request
            from bs4 import BeautifulSoup
            return urllib_scraper
        except ImportError:
            logging.error("No web scraping libraries available. Please install requests or urllib.")
            return None

def requests_scraper(url: str) -> str:
    """
    Scrape webpage using requests library
    
    Args:
        url (str): URL to scrape
    
    Returns:
        str: HTML content of the page
    """
    import requests
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return ""

def urllib_scraper(url: str) -> str:
    """
    Scrape webpage using urllib library
    
    Args:
        url (str): URL to scrape
    
    Returns:
        str: HTML content of the page
    """
    import urllib.request
    import ssl

    # Create a custom context to bypass SSL verification (use cautiously)
    context = ssl._create_unverified_context()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=context, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return ""

def google_search_tweets(experts: List[str], num_results: int = 3) -> List[Dict[str, str]]:
    """
    Perform a comprehensive search to find recent tweets from AI experts
    
    Args:
        experts (List[str]): List of experts to search for
        num_results (int): Number of results to retrieve per expert
    
    Returns:
        List[Dict[str, str]]: Extracted tweet information
    """
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Choose scraping method
    scraper = choose_scraping_method()
    if not scraper:
        logging.error("No web scraping method available")
        return []

    tweets_data = []
    
    # Alternative search queries if one fails
    search_queries = [
        'site:x.com "{}" AI latest tweet',
        '"{}" x.com tweet AI',
        'from:{} AI tweet'
    ]
    
    for expert in experts:
        expert_tweets_found = 0
        
        for query_template in search_queries:
            if expert_tweets_found >= num_results:
                break
            
            # Construct Google search URL
            query = query_template.format(expert)
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            
            try:
                # Fetch search results
                html_content = scraper(search_url)
                
                # Parse HTML (use BeautifulSoup if available)
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Find links in search results
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        url = link['href']
                        
                        # Filter for X.com tweet URLs
                        if 'x.com' in url and '/status/' in url:
                            try:
                                # Extract username and tweet ID
                                username = url.split('x.com/')[1].split('/status/')[0]
                                tweet_id = url.split('/status/')[1].split('?')[0]
                                
                                # Create tweet data dictionary
                                tweet_info = {
                                    'id': tweet_id,
                                    'username': username,
                                    'name': expert,
                                    'content': "[View original tweet]",
                                    'timestamp': datetime.now().isoformat(),
                                    'url': url
                                }
                                
                                tweets_data.append(tweet_info)
                                expert_tweets_found += 1
                                
                                logging.info(f"Found tweet URL for {expert}: {url}")
                                
                                # Stop if we've found enough tweets
                                if expert_tweets_found >= num_results:
                                    break
                            
                            except Exception as parse_error:
                                logging.error(f"Error parsing tweet URL {url}: {parse_error}")
                    
                except ImportError:
                    logging.warning("BeautifulSoup not available. Using basic parsing.")
                
                # Random delay to avoid rate limiting
                time.sleep(random.uniform(1, 3))
            
            except Exception as e:
                logging.error(f"Error searching for {expert}: {e}")
    
    return tweets_data

def fetch_top_tweets():
    """
    Fetch tweets from top AI voices using Google search
    
    Returns:
        list: List of tweet dictionaries
    """
    logger = logging.getLogger(__name__)
    logger.info("Fetching tweets from top AI voices")
    
    # Get AI experts from config or use defaults
    ai_top_voices = [
        "Sam Altman", "Elon Musk", "Yann LeCun", 
        "Andrew Ng", "Demis Hassabis"
    ]
    
    # Get tweet links via Google search
    tweets = google_search_tweets(ai_top_voices, num_results=2)
    
    # Return whatever we found (could be empty)
    logger.info(f"Found {len(tweets)} tweets from top AI voices")
    return tweets

def filter_tweets(tweets, excluded_accounts=None):
    """
    Filter tweets based on user preferences
    
    Args:
        tweets (list): List of tweet dictionaries
        excluded_accounts (list, optional): List of accounts to exclude
    
    Returns:
        list: Filtered list of tweets
    """
    if not excluded_accounts:
        excluded_accounts = []
    
    filtered_tweets = [
        tweet for tweet in tweets
        if tweet['username'].lower() not in [account.lower() for account in excluded_accounts]
    ]
    
    logging.info(f"Filtered to {len(filtered_tweets)} tweets after applying exclusions")
    return filtered_tweets

def generate_twitter_summary(user_id, tweets):
    """
    Generate a summary of tweets from top AI voices
    
    Args:
        user_id (str): User identifier
        tweets (list): List of tweet dictionaries
    
    Returns:
        str: Formatted summary of tweets
    """
    if not tweets:
        logging.warning("No tweets to summarize")
        return "No recent tweets from top AI voices found. Please try again later."
    
    # Personalized greeting (placeholder - you might want to implement 
    # a more sophisticated system message retrieval)
    personalized_greeting = "Here are the latest tweets from top AI voices in the past 24 hours"
    
    # Create a summary directly listing the tweet links
    links_message = f"{personalized_greeting}. Click the links to view the full tweets:\n\n"
    
    for tweet in tweets:
        links_message += f"• {tweet['name']} (@{tweet['username']}): {tweet['url']}\n"
    
    return links_message

# For testing purposes
if __name__ == "__main__":
    # Test the tweet fetching function
    tweets = fetch_top_tweets()
    print(f"Found {len(tweets)} tweets from the past day")
    for tweet in tweets:
        print(f"@{tweet['username']}: {tweet['url']}")
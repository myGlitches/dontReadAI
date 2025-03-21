import logging
import random
import time
from typing import List, Dict

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
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
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
                                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
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

# Example usage
if __name__ == '__main__':
    # List of AI experts to search
    experts = [
        "Sam Altman", 
        "Elon Musk", 
        "Yann LeCun", 
        "Andrew Ng", 
        "Demis Hassabis"
    ]
    
    # Fetch tweets
    tweets = google_search_tweets(experts)
    
    # Print results
    print(f"Found {len(tweets)} tweets:")
    for tweet in tweets:
        print(f"{tweet['name']} (@{tweet['username']}): {tweet['url']}")
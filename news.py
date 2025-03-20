# news.py
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from utils import fetch_from_hackernews, fetch_from_techcrunch, filter_by_keywords, rank_news_by_relevance


def fetch_ai_news(user_preferences):
    """Fetch and filter AI news based on user preferences"""
    # Get raw news from sources
    all_news = []
    all_news.extend(fetch_from_hackernews())
    all_news.extend(fetch_from_techcrunch())
    
    # Apply first-level filtering based on keywords
    filtered_news = filter_by_keywords(all_news)
    
    # Apply user preference filtering
    if user_preferences:
        # Filter out excluded topics
        exclusions = user_preferences.get("exclusions", [])
        filtered_news = [news for news in filtered_news if 
                        not any(excl.lower() in news['title'].lower() for excl in exclusions)]
        
        # Rank by relevance to interests
        filtered_news = rank_news_by_relevance(filtered_news, user_preferences)
    
    return filtered_news[:5]  # Return top 5 results
import requests
from datetime import datetime, timedelta
import logging
from bs4 import BeautifulSoup
from utils import fetch_from_hackernews, fetch_from_techcrunch, filter_by_keywords
from news_analysis import analyze_news_relevance, generate_digest

# Set up logging
logger = logging.getLogger(__name__)

def fetch_ai_news(user_id, user_preferences, include_summaries=True, max_results=3):
    """Fetch and filter AI news based on user preferences with enhanced analysis"""
    logger.info(f"Fetching AI news for user {user_id}")
    
    # Get raw news from sources
    hackernews_items = fetch_from_hackernews()
    logger.info(f"Fetched {len(hackernews_items)} items from HackerNews")
    
    techcrunch_items = fetch_from_techcrunch()
    logger.info(f"Fetched {len(techcrunch_items)} items from TechCrunch")
    
    all_news = hackernews_items + techcrunch_items
    logger.info(f"Total news items fetched: {len(all_news)}")
    
    # Apply first-level filtering based on keywords
    filtered_news = filter_by_keywords(all_news)
    logger.info(f"Items after keyword filtering: {len(filtered_news)}")
    
    # Record the titles being processed
    logger.info("Processing news items:")
    for idx, item in enumerate(filtered_news[:10]):
        logger.info(f"{idx+1}. {item.get('title')} | Source: {item.get('source')}")
    
    # Filter out news the user has already seen
    from db import has_viewed_news
    not_viewed = []
    for item in filtered_news:
        if not has_viewed_news(user_id, item):
            not_viewed.append(item)
        else:
            logger.info(f"Skipping already viewed: {item.get('title')}")
    
    logger.info(f"New unseen items: {len(not_viewed)}")
    
    # Apply user preference filtering
    filtered_by_preferences = not_viewed
    if user_preferences:
        # Filter out excluded topics
        exclusions = user_preferences.get("exclusions", [])
        if exclusions:
            logger.info(f"Filtering out user exclusions: {exclusions}")
            filtered_by_preferences = [news for news in not_viewed if 
                            not any(excl.lower() in news['title'].lower() for excl in exclusions)]
    
    logger.info(f"Items after exclusion filtering: {len(filtered_by_preferences)}")
    
    # Take candidates for deep analysis (more than we need to ensure we have enough after analysis)
    candidates = filtered_by_preferences[:min(10, len(filtered_by_preferences))]
    logger.info(f"Selected {len(candidates)} candidates for detailed analysis")
    
    # Ensure we have at least 3 candidates, even if they're already viewed
    if len(candidates) < 3:
        logger.info("Not enough new articles, including some already viewed ones")
        additional_needed = 3 - len(candidates)
        for item in filtered_news:
            if item not in candidates:
                candidates.append(item)
                additional_needed -= 1
                if additional_needed <= 0:
                    break
    
    # Perform detailed relevance analysis on each candidate
    analyzed_news = []
    for i, news_item in enumerate(candidates):
        logger.info(f"Analyzing relevance for: {news_item.get('title')}")
        
        # First do a quick analysis without summary to get relevance scores
        analysis = analyze_news_relevance(news_item, user_preferences, include_summary=False)
        relevance_score = analysis.get("relevance_score", 5)
        
        logger.info(f"Relevance score: {relevance_score}/10 for '{news_item.get('title')}'")
        
        # Add analysis data to news item
        news_item["relevance_score"] = relevance_score
        news_item["relevance_explanation"] = analysis.get("explanation", "")
        news_item["topics"] = analysis.get("topics", [])
        
        analyzed_news.append(news_item)
    
    # Sort by relevance score (descending)
    analyzed_news.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    # Get top results based on relevance
    top_results = analyzed_news[:max_results]
    logger.info(f"Selected top {len(top_results)} results based on relevance")
    
    # Now for the top results, generate summaries if needed
    if include_summaries:
        for i, news_item in enumerate(top_results):
            logger.info(f"Generating summary for: {news_item.get('title')}")
            
            # Get full analysis with summary for top results
            full_analysis = analyze_news_relevance(news_item, user_preferences, include_summary=True)
            news_item["summary"] = full_analysis.get("summary", "")
    
    # Record these news items as viewed
    if top_results:
        from db import add_viewed_news
        for news in top_results:
            add_viewed_news(user_id, news)
            logger.info(f"Marked as viewed: {news.get('title')}")
    
    logger.info(f"Returning {len(top_results)} news items")
    return top_results

def generate_news_digest_for_user(user_id, user_preferences):
    """Generate a comprehensive digest of recent AI funding news"""
    logger.info(f"Generating news digest for user {user_id}")
    
    # Get more news items for the digest (without summaries initially)
    news_items = fetch_ai_news(user_id, user_preferences, include_summaries=False, max_results=5)
    logger.info(f"Selected {len(news_items)} items for digest")
    
    # For digest generation, we need summaries
    for item in news_items:
        if "summary" not in item or not item["summary"]:
            logger.info(f"Getting summary for digest item: {item.get('title')}")
            analysis = analyze_news_relevance(item, user_preferences, include_summary=True)
            item["summary"] = analysis.get("summary", "")
    
    # Generate the digest
    logger.info("Generating combined digest")
    digest = generate_digest(news_items, user_preferences)
    
    logger.info("Digest generation complete")
    return {
        "digest": digest,
        "news_count": len(news_items),
        "date": datetime.now().strftime("%Y-%m-%d")
    }
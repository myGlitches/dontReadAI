import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from utils import fetch_from_hackernews, fetch_from_techcrunch, filter_by_keywords
from news_analysis import analyze_news_relevance, generate_digest

def fetch_ai_news(user_id, user_preferences, include_summaries=True, max_results=5):
    """Fetch and filter AI news based on user preferences with enhanced analysis"""
    # Get raw news from sources
    all_news = []
    all_news.extend(fetch_from_hackernews())
    all_news.extend(fetch_from_techcrunch())
    
    # Apply first-level filtering based on keywords
    filtered_news = filter_by_keywords(all_news)
    
    # Filter out news the user has already seen
    from db import has_viewed_news
    filtered_news = [news for news in filtered_news if not has_viewed_news(user_id, news)]
    
    # Apply user preference filtering
    if user_preferences:
        # Filter out excluded topics
        exclusions = user_preferences.get("exclusions", [])
        filtered_news = [news for news in filtered_news if 
                         not any(excl.lower() in news['title'].lower() for excl in exclusions)]
    
    # Limit candidates for deep analysis to avoid too many API calls
    # Process at most 10 articles for detailed analysis
    candidates = filtered_news[:10]
    
    # Perform detailed relevance analysis on each candidate
    analyzed_news = []
    for news_item in candidates:
        # First do a quick analysis without summary to get relevance scores
        analysis = analyze_news_relevance(news_item, user_preferences, include_summary=False)
        
        # Add analysis data to news item
        news_item["relevance_score"] = analysis.get("relevance_score", 5)
        news_item["relevance_explanation"] = analysis.get("explanation", "")
        news_item["topics"] = analysis.get("topics", [])
        
        analyzed_news.append(news_item)
    
    # Sort by relevance score (descending)
    analyzed_news.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    # Get top results based on relevance
    top_results = analyzed_news[:max_results]
    
    # Now for the top results, generate summaries if needed
    if include_summaries:
        for news_item in top_results:
            # Get full analysis with summary for top results
            full_analysis = analyze_news_relevance(news_item, user_preferences, include_summary=True)
            news_item["summary"] = full_analysis.get("summary", "")
    
    # Record these news items as viewed
    if top_results:
        from db import add_viewed_news
        for news in top_results:
            add_viewed_news(user_id, news)
    
    return top_results

def generate_news_digest_for_user(user_id, user_preferences):
    """Generate a comprehensive digest of recent AI funding news"""
    # Get more news items for the digest (without summaries initially)
    news_items = fetch_ai_news(user_id, user_preferences, include_summaries=False, max_results=7)
    
    # For digest generation, we need summaries
    for item in news_items:
        if "summary" not in item or not item["summary"]:
            analysis = analyze_news_relevance(item, user_preferences, include_summary=True)
            item["summary"] = analysis.get("summary", "")
    
    # Generate the digest
    digest = generate_digest(news_items, user_preferences)
    
    return {
        "digest": digest,
        "news_count": len(news_items),
        "date": datetime.now().strftime("%Y-%m-%d")
    }
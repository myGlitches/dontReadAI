# /config.py - Configuration settings for the AI News Bot
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Validate required environment variables
if not all([TELEGRAM_TOKEN, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    missing = [k for k, v in {
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'OPENAI_API_KEY': OPENAI_API_KEY,
        'SUPABASE_URL': SUPABASE_URL,
        'SUPABASE_KEY': SUPABASE_KEY
    }.items() if not v]
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")


# News Service Settings
NEWS_UPDATE_TIME = "22:00"  # 10 PM in 24-hour format

# Twitter Service Settings
TWITTER_VOICES = [
    "Sam Altman",
    "Elon Musk",
    "Yann LeCun",
    "Andrew Ng", 
    "Demis Hassabis",
    "Geoffrey Hinton",
    "Fei-Fei Li",
    "Ilya Sutskever",
    "Andrej Karpathy",
    "Dario Amodei"
]

# Default system message for each service
DEFAULT_NEWS_SYSTEM_MESSAGE = """
You are an AI funding news specialist. You analyze and summarize news about AI companies receiving funding, investments, or acquisitions.
Your goal is to provide concise, informative summaries focusing on:
1. The company name
2. The amount of funding
3. The funding series/stage (Seed, Series A, etc.)
4. The investors
5. Brief details on what the company does and plans to do with the funding
"""

DEFAULT_TWITTER_SYSTEM_MESSAGE = """
You are a Twitter AI voice summarizer. You analyze and summarize tweets from leading AI voices in the industry.
Your goal is to provide a concise overview of key insights, announcements, and trends from these influential figures.
Focus on extracting the most valuable information and connecting related discussions or themes.
"""

# Logging
LOG_LEVEL = "INFO"
import re
from openai import OpenAI
from config import OPENAI_API_KEY

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Original functions from utils.py would remain...

def help_command(update, context):
    """Show enhanced help information"""
    help_text = (
        "🤖 *AI Funding News Bot* 🤖\n\n"
        "Get personalized AI funding and investment news with AI-powered insights.\n\n"
        "*Available Commands:*\n"
        "/start - Initialize the bot and set up preferences\n"
        "/news - Get personalized AI funding news with summaries\n"
        "/digest - Generate a comprehensive digest of recent AI funding news\n"
        "/interests - View your current interest topics\n"
        "/add\\_tag TAG \\[weight\\] - Add a new interest (e.g., /add\\_tag computer\\_vision 0.9)\n"
        "/remove\\_tag TAG - Remove an interest (e.g., /remove\\_tag blockchain)\n"
        "/adjust\\_interest TAG WEIGHT - Change priority of an interest\n"
        "/history - View your recently read news\n"
        "/clear\\_history - Clear your news history\n"
        "/reset - Reset your preferences and start over\n"
        "/help - Show this help message\n\n"
        "The bot uses AI to analyze news articles, provide summaries relevant to your interests, and generate insights tailored to your professional role."
    )
    
    try:
        update.message.reply_text(help_text, parse_mode='MarkdownV2')
    except Exception as e:
        # Fallback to plain text if Markdown fails
        fallback_text = (
            "🤖 AI Funding News Bot 🤖\n\n"
            "Get personalized AI funding and investment news with AI-powered insights.\n\n"
            "Available Commands:\n"
            "/start - Initialize the bot and set up preferences\n"
            "/news - Get personalized AI funding news with summaries\n"
            "/digest - Generate a comprehensive digest of recent AI funding news\n"
            "/interests - View your current interest topics\n"
            "/add_tag TAG [weight] - Add a new interest\n"
            "/remove_tag TAG - Remove an interest\n"
            "/adjust_interest TAG WEIGHT - Change priority of an interest\n"
            "/history - View your recently read news\n"
            "/clear_history - Clear your news history\n"
            "/reset - Reset your preferences and start over\n"
            "/help - Show this help message\n\n"
            "The bot uses AI to analyze news articles, provide summaries relevant to your interests, and generate insights tailored to your professional role."
        )
        update.message.reply_text(fallback_text)
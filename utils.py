# utils.py - Utility functions

import logging
from datetime import datetime
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_content_id(content):
    """Generate a unique ID for content"""
    if isinstance(content, str):
        content_str = content
    elif isinstance(content, list):
        # For lists of items (like tweets or news)
        # Create a string from the first 3 items' titles or content
        content_str = "".join([str(item.get('title', item.get('content', ''))) 
                              for item in content[:3]])
    else:
        content_str = str(content)
    
    # Add timestamp to make it unique
    content_str += datetime.now().isoformat()
    
    # Generate MD5 hash
    return hashlib.md5(content_str.encode()).hexdigest()

def format_message_for_telegram(message):
    """Format message for Telegram, escaping special characters"""
    # Escape special characters for Markdown V2
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        message = message.replace(char, f"\\{char}")
    
    return message

def split_long_message(message, max_length=4000):
    """Split long message into smaller chunks for Telegram"""
    if len(message) <= max_length:
        return [message]
    
    # Find a good splitting point (end of paragraph)
    split_points = [i for i, char in enumerate(message[:max_length]) if char == '\n']
    
    if not split_points:
        # If no paragraph breaks, split at space
        split_points = [i for i, char in enumerate(message[:max_length]) if char == ' ']
    
    if not split_points:
        # If no good splitting point, split at max_length
        split_point = max_length
    else:
        # Split at the last paragraph or space before max_length
        split_point = split_points[-1] + 1
    
    first_part = message[:split_point]
    remaining = message[split_point:]
    
    # Recursively split the remaining message
    return [first_part] + split_long_message(remaining, max_length)
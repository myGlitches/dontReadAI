# feedback_handler.py - Handle and process user feedback

import logging
import json
from openai import OpenAI
from config import OPENAI_API_KEY
from db import log_user_feedback, get_user_system_message, update_user_system_message, update_excluded_items

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def process_feedback(user_id, service_type, content_id, feedback_type, feedback_reason=None):
    """Process user feedback and update preferences"""
    # Log the feedback
    log_user_feedback(user_id, service_type, content_id, feedback_type, feedback_reason)
    
    # If feedback is positive, nothing more to do
    if feedback_type == 'positive':
        logger.info(f"Positive feedback from user {user_id} for {service_type} - no changes needed")
        return "Thanks for your feedback! I'll continue to provide similar updates."
    
    # If negative feedback but no reason provided, we can't adjust preferences
    if not feedback_reason:
        logger.info(f"Negative feedback from user {user_id} for {service_type} but no reason provided")
        return "Thanks for your feedback. To help me improve, please provide a reason for your dislike."
    
    # Process negative feedback with reason
    logger.info(f"Processing negative feedback from user {user_id} for {service_type}: {feedback_reason}")
    
    # Extract exclusions and modify system message based on feedback
    exclusions = extract_exclusions(feedback_reason, service_type)
    
    # Apply any identified exclusions
    for exclusion in exclusions:
        update_excluded_items(user_id, service_type, exclusion, add=True)
        logger.info(f"Added exclusion for user {user_id}: {exclusion}")
    
    # Update system message based on feedback
    current_system_message = get_user_system_message(user_id, service_type)
    new_system_message = modify_system_message(current_system_message, feedback_reason, service_type)
    
    # Save the updated system message
    if new_system_message != current_system_message:
        update_user_system_message(user_id, service_type, new_system_message)
        logger.info(f"Updated system message for user {user_id} for {service_type}")
    
    return "Thanks for your feedback! I've adjusted my recommendations based on your preferences."

def extract_exclusions(feedback_reason, service_type):
    """Extract specific exclusions from feedback reason"""
    exclusions = []
    
    try:
        # Use AI to analyze feedback and extract exclusions
        prompt = f"""
        Analyze this user feedback about {"AI funding news" if service_type == 'news' else "Twitter AI voices"} 
        and extract ONLY specific items that should be excluded from future content.
        
        User feedback: "{feedback_reason}"
        
        For news content, extract specific regions, topics, or companies to exclude.
        For Twitter content, extract specific Twitter accounts to exclude.
        
        Respond with JSON only in this format:
        {{
            "exclusions": ["item1", "item2"],
            "reason": "brief explanation of why these items were identified"
        }}
        
        If no clear exclusions can be identified, return an empty list.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant that analyzes user feedback."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        result = json.loads(response.choices[0].message.content)
        exclusions = result.get("exclusions", [])
        
        logger.info(f"Extracted exclusions: {exclusions}")
        return exclusions
        
    except Exception as e:
        logger.error(f"Error extracting exclusions: {str(e)}")
        return []

def modify_system_message(current_message, feedback_reason, service_type):
    """Modify the system message based on user feedback"""
    try:
        # Use AI to analyze feedback and modify the system message
        prompt = f"""
        You are a prompt engineering expert. Modify this system message for an AI assistant that provides 
        {"AI funding news summaries" if service_type == 'news' else "Twitter AI voices summaries"} 
        based on the following user feedback.
        
        CURRENT SYSTEM MESSAGE:
        {current_message}
        
        USER FEEDBACK:
        "{feedback_reason}"
        
        Analyze the feedback and make minimal, targeted changes to the system message to address 
        the user's concerns while maintaining the core functionality.
        
        IMPORTANT:
        - Only modify what's necessary
        - Keep the same overall structure and purpose
        - Do not remove crucial instructions
        - Ensure the modified message is complete
        
        Return the complete modified system message only - do not include explanations or 
        the original message.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a prompt engineering expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        new_message = response.choices[0].message.content.strip()
        
        # Ensure we don't get back an empty message
        if len(new_message) < 50:
            logger.warning(f"Modified system message too short, keeping original: {new_message}")
            return current_message
            
        logger.info(f"System message modified based on feedback")
        return new_message
        
    except Exception as e:
        logger.error(f"Error modifying system message: {str(e)}")
        return current_message
# feedback.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from preferences import update_preferences_from_feedback

def add_feedback_buttons(update, context, news_items):
    """Add simple feedback buttons to news items"""
    context.user_data['current_news'] = news_items
    
    for i, item in enumerate(news_items):
        keyboard = [[
            InlineKeyboardButton("👍 Relevant", callback_data=f"like_{i}"),
            InlineKeyboardButton("👎 Not Relevant", callback_data=f"dislike_{i}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(f"Was this relevant?", reply_markup=reply_markup)

def handle_feedback(update, context):
    """Process user feedback"""
    query = update.callback_query
    query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    # Handle the different callback data formats
    if data.startswith('like_'):
        action = 'like'
        index = int(data.split('_')[1])
        
        # Process like feedback
        news_item = context.user_data['current_news'][index]
        update_preferences_from_feedback(user_id, news_item, "like")
        query.edit_message_text("Thanks for your feedback! I'll show more like this.")
        
    elif data.startswith('dislike_'):
        action = 'dislike'
        index = int(data.split('_')[1])
        
        # Ask for reason
        keyboard = [[
            InlineKeyboardButton("Not interested in this region", 
                               callback_data=f"reason_region_{index}"),
            InlineKeyboardButton("Too technical", 
                               callback_data=f"reason_technical_{index}"),
            InlineKeyboardButton("Already knew this", 
                               callback_data=f"reason_knew_{index}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("Why wasn't this relevant?", reply_markup=reply_markup)
        
    elif data.startswith('reason_'):
        parts = data.split('_')
        reason_type = parts[1]
        index = int(parts[2])
        
        # Process dislike with reason
        news_item = context.user_data['current_news'][index]
        update_preferences_from_feedback(user_id, news_item, "dislike", f"not_interested_{reason_type}")
        query.edit_message_text(f"Thanks! I'll adjust recommendations based on your feedback.")
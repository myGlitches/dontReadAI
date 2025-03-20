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
    
    # Extract the action and news index
    action, index = data.split('_')
    index = int(index)
    news_item = context.user_data['current_news'][index]
    
    if action == "like":
        # Handle like feedback
        update_preferences_from_feedback(user_id, news_item, "like")
        query.edit_message_text("Thanks for your feedback! I'll show more like this.")
        
    elif action == "dislike":
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
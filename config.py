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
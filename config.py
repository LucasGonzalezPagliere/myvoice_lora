"""
Configuration settings for the iMessage data processing pipeline.
"""

# Database settings
DEFAULT_DB_PATH = None  # Will use ~/Library/Messages/chat.db

# Output settings
OUTPUT_CSV_PATH = "training_data.csv"

# History settings
# DAYS_BACK = 365  # Number of days back in history to process (set to None for all history)
# Examples:
# DAYS_BACK = 1      # Only process last 24 hours
# DAYS_BACK = 7      # Only process last week
DAYS_BACK = 30     # Only process last month
# DAYS_BACK = 365    # Only process last year
# DAYS_BACK = None   # Process all history (default)

# Filtering settings
MIN_MESSAGE_LENGTH = 2  # Minimum characters for a valid message
MAX_MESSAGE_LENGTH = 1000  # Maximum characters for a message (to avoid extremely long messages)

# Turn grouping settings
MAX_TURN_GAP_SECONDS = 3000  # Maximum gap between messages to group them in the same turn (5 minutes)

# Training example settings
CONVERSATION_STARTER_TOKEN = "[CONVERSATION_STARTER]"
IMAGE_PLACEHOLDER = "[IMAGE]"
URL_PLACEHOLDER = "[URL]"
VIDEO_PLACEHOLDER = "[VIDEO]"
AUDIO_PLACEHOLDER = "[AUDIO]"
FILE_PLACEHOLDER = "[FILE]"

# Logging settings
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Data quality settings
REMOVE_EMPTY_EXAMPLES = True
REMOVE_DUPLICATE_EXAMPLES = True
MIN_EXAMPLE_COUNT = 3  # Minimum number of examples to keep a conversation

# Conversation settings
PROCESS_GROUP_CHATS = False # Set to True to include group conversations (3+ participants) 
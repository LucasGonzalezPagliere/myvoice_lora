import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import List, Tuple, Optional, Dict, Set
import logging
from config import DAYS_BACK, PROCESS_GROUP_CHATS

# Import pyobjc libraries for NSAttributedString decoding
try:
    from Foundation import NSData, NSKeyedUnarchiver, NSUnarchiver
    PYOBJC_AVAILABLE = True
except ImportError:
    PYOBJC_AVAILABLE = False
    logging.warning("pyobjc-framework-Foundation not found. Attributed body decoding will be limited.")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class iMessageProcessor:
    def __init__(self, db_path: str = None):
        """
        Initialize the iMessage processor.
        
        Args:
            db_path: Path to the chat.db file. If None, uses default location.
        """
        if db_path is None:
            # Default path for macOS iMessage database
            home = Path.home()
            self.db_path = home / "Library" / "Messages" / "chat.db"
        else:
            self.db_path = Path(db_path)
            
        self.connection = None
        
    def connect_to_database(self) -> bool:
        """
        Connect to the iMessage database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not self.db_path.exists():
                logger.error(f"Database not found at {self.db_path}")
                logger.error("Make sure you have Full Disk Access permission enabled")
                return False
                
            self.connection = sqlite3.connect(str(self.db_path))
            logger.info(f"Successfully connected to database at {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def close_connection(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def convert_messages_timestamp(self, timestamp: int) -> datetime:
        """
        Convert Messages.app timestamp to Python datetime.
        
        Args:
            timestamp: Messages.app timestamp (nanoseconds since 2001-01-01)
            
        Returns:
            datetime: Python datetime object
        """
        try:
            # Messages.app uses nanoseconds since 2001-01-01 00:00:00 UTC
            # Convert to seconds and add the 2001 epoch offset
            unix_timestamp = (timestamp / 1_000_000_000) + 978307200
            return datetime.fromtimestamp(unix_timestamp)
        except (OSError, ValueError):
            # Handle invalid timestamps by returning current time
            logger.warning(f"Invalid timestamp {timestamp}, using current time")
            return datetime.now()
    
    def decode_attributed_body(self, data: bytes) -> Optional[str]:
        """
        Decode attributedBody data from Messages database.
        
        Args:
            data: Raw attributedBody data
            
        Returns:
            str: Decoded text or None if decoding fails
        """
        if not data:
            return None

        if not PYOBJC_AVAILABLE:
            # Fallback to simple UTF-8 decoding if pyobjc is not available
            try:
                return data.decode('utf-8', errors='ignore').strip()
            except Exception:
                return None

        ns_data = NSData.dataWithBytes_length_(data, len(data))

        # 1. Modern keyed archiver (macOS 11+)
        try:
            unarchiver = NSKeyedUnarchiver.alloc().initForReadingWithData_(ns_data)
            unarchiver.setRequiresSecureCoding_(False)
            decoded_object = unarchiver.decodeObjectForKey_("root")
            if decoded_object and hasattr(decoded_object, 'string'):
                return str(decoded_object.string())
        except Exception as e:
            logging.debug(f"NSKeyedUnarchiver failed: {e}")

        # 2. Legacy (non-keyed) archiver
        try:
            decoded_object = NSUnarchiver.unarchiveObjectWithData_(ns_data)
            if decoded_object and hasattr(decoded_object, 'string'):
                return str(decoded_object.string())
        except Exception as e:
            logging.debug(f"NSUnarchiver failed: {e}")
            
        # 3. Fallback to raw UTF-8
        try:
            text = data.decode('utf-8', errors='ignore').strip()
            # Often the text is hidden inside null bytes
            clean_text = ''.join(char for char in text if char.isprintable())
            if len(clean_text) > 2:
                return clean_text
        except Exception:
            pass

        logger.warning("Failed to decode attributedBody with all methods.")
        return None
    
    def extract_message_text(self, text: str, attributed_body: bytes) -> Optional[str]:
        """
        Extract text from message, handling both text and attributedBody columns.
        
        Args:
            text: Text from the 'text' column
            attributed_body: Data from the 'attributedBody' column
            
        Returns:
            str: Extracted text or None if no valid text found
        """
        # Try text column first
        if text and text.strip():
            return text.strip()
        
        # Fall back to attributedBody
        if attributed_body:
            return self.decode_attributed_body(attributed_body)
        
        return None
    
    def is_junk_message(self, text: str) -> bool:
        """
        Check if a message should be filtered out as junk.
        
        Args:
            text: Message text to check
            
        Returns:
            bool: True if message should be filtered out
        """
        if not text:
            return True
            
        # Check for tapbacks
        tapback_patterns = [
            r'^(Liked|Loved|Laughed at|Disliked|Emphasized|Questioned)',
            r'^(Liked|Loved|Laughed at|Disliked|Emphasized|Questioned) ".*"$'
        ]
        
        for pattern in tapback_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Check for messages that are just attachments
        attachment_patterns = [
            r'^\[IMAGE\]$',
            r'^\[URL\]$',
            r'^\[VIDEO\]$',
            r'^\[AUDIO\]$',
            r'^\[FILE\]$'
        ]
        
        for pattern in attachment_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Check for very short messages that might be noise
        if len(text.strip()) < 2:
            return True
            
        return False
    
    def get_all_conversations(self) -> Dict[str, List[int]]:
        """
        Groups all chats by their participants, returning a dictionary mapping a unique
        participant key to a list of associated chat_ids.
        """
        if not self.connection:
            logger.error("No database connection")
            return {}

        query = """
            SELECT
                c.ROWID as chat_id,
                GROUP_CONCAT(h.id, ',') as participants
            FROM chat c
            JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
            JOIN handle h ON chj.handle_id = h.ROWID
            GROUP BY c.ROWID
            ORDER BY c.ROWID;
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Use a dictionary to group chat_ids by the set of participants
            conversations = {}
            for chat_id, participants_str in cursor.fetchall():
                if participants_str:
                    # Sort participants to create a consistent, unique key for the group
                    participants = tuple(sorted(participants_str.split(',')))
                    if participants not in conversations:
                        conversations[participants] = []
                    conversations[participants].append(chat_id)
            
            logger.info(f"Identified {len(conversations)} unique conversations (groups of participants).")
            return conversations

        except Exception as e:
            logger.error(f"Error getting all conversations: {e}")
            return {}

    def get_messages_for_conversation(self, chat_ids: List[int]) -> List[Dict]:
        """
        Fetches and combines all messages from a list of chat_ids,
        representing a single logical conversation.
        """
        if not self.connection or not chat_ids:
            return []
        
        # Calculate the cutoff date if DAYS_BACK is set
        cutoff_date = None
        if DAYS_BACK is not None:
            cutoff_date = datetime.now() - timedelta(days=DAYS_BACK)
            # Convert to Messages.app timestamp format (nanoseconds since 2001-01-01)
            cutoff_timestamp = int((cutoff_date.timestamp() - 978307200) * 1_000_000_000)
            logger.info(f"Processing messages from {cutoff_date.strftime('%Y-%m-%d')} onwards")
        
        placeholders = ','.join('?' for _ in chat_ids)
        
        # Build query with optional date filter
        if cutoff_date:
            query = f"""
                SELECT 
                    m.ROWID as message_id,
                    m.text,
                    m.attributedBody,
                    m.date,
                    m.is_from_me,
                    h.id as handle_id,
                    h.uncanonicalized_id as phone_number
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                INNER JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                WHERE cmj.chat_id IN ({placeholders}) AND m.date >= ?
                ORDER BY m.date ASC
            """
            params = chat_ids + [cutoff_timestamp]
        else:
            query = f"""
                SELECT 
                    m.ROWID as message_id,
                    m.text,
                    m.attributedBody,
                    m.date,
                    m.is_from_me,
                    h.id as handle_id,
                    h.uncanonicalized_id as phone_number
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                INNER JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                WHERE cmj.chat_id IN ({placeholders})
                ORDER BY m.date ASC
            """
            params = chat_ids
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                message_id, text, attributed_body, date, is_from_me, handle_id, phone_number = row
                
                # Extract text
                extracted_text = self.extract_message_text(text, attributed_body)
                
                if extracted_text and not self.is_junk_message(extracted_text):
                    messages.append({
                        'message_id': message_id,
                        'text': extracted_text,
                        'date': self.convert_messages_timestamp(date),
                        'is_from_me': bool(is_from_me),
                        'sender_id': handle_id,
                        'phone_number': phone_number
                    })
            
            # Because messages from multiple chats are combined, we must sort them
            # again in Python to ensure perfect chronological order.
            messages.sort(key=lambda m: m['date'])
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching messages for conversation: {e}")
            return []
    
    def group_messages_into_turns(self, messages: List[Dict]) -> List[Dict]:
        """
        Group consecutive messages from the same sender into turns.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List[Dict]: List of turn dictionaries
        """
        if not messages:
            return []
        
        turns = []
        current_turn = {
            'sender_id': messages[0]['sender_id'],
            'is_from_me': messages[0]['is_from_me'],
            'messages': [messages[0]['text']],
            'start_time': messages[0]['date'],
            'end_time': messages[0]['date']
        }
        
        for message in messages[1:]:
            # If same sender, add to current turn
            if (message['sender_id'] == current_turn['sender_id'] and 
                message['is_from_me'] == current_turn['is_from_me']):
                current_turn['messages'].append(message['text'])
                current_turn['end_time'] = message['date']
            else:
                # Different sender, save current turn and start new one
                current_turn['text'] = ' '.join(current_turn['messages'])
                turns.append(current_turn)
                
                current_turn = {
                    'sender_id': message['sender_id'],
                    'is_from_me': message['is_from_me'],
                    'messages': [message['text']],
                    'start_time': message['date'],
                    'end_time': message['date']
                }
        
        # Add the last turn
        current_turn['text'] = ' '.join(current_turn['messages'])
        turns.append(current_turn)
        
        return turns
    
    def create_training_examples(self, turns: List[Dict]) -> List[Tuple[str, str]]:
        """
        Create training examples from turns.
        
        Args:
            turns: List of turn dictionaries
            
        Returns:
            List[Tuple[str, str]]: List of (input, output) pairs
        """
        examples = []
        
        for i, turn in enumerate(turns):
            if turn['is_from_me']:  # This is your turn
                # Find the previous turn (from the other person)
                if i > 0:
                    input_text = turns[i-1]['text']
                else:
                    input_text = "[CONVERSATION_STARTER]"
                
                output_text = turn['text']
                
                examples.append((input_text, output_text))
        
        return examples
    
    def process_all_conversations(self) -> List[Tuple[str, str]]:
        """
        Processes all conversations by participant groups and creates training examples.
        """
        if not self.connect_to_database():
            return []
        
        try:
            all_examples = []
            # Get conversations grouped by participants
            conversations = self.get_all_conversations()
            
            # Filter for 1-on-1 chats if PROCESS_GROUP_CHATS is False
            if not PROCESS_GROUP_CHATS:
                initial_count = len(conversations)
                # A 1-on-1 chat has exactly 2 participants in our model (you and the other person)
                conversations = {p: cids for p, cids in conversations.items() if len(p) == 1}
                logger.info(f"Filtered for 1-on-1 conversations. Kept {len(conversations)} of {initial_count} total conversations.")

            # Log the date range being processed
            if DAYS_BACK is not None:
                cutoff_date = datetime.now() - timedelta(days=DAYS_BACK)
                logger.info(f"Processing conversations from {cutoff_date.strftime('%Y-%m-%d')} onwards (last {DAYS_BACK} days)")
            else:
                logger.info("Processing all conversations (no date limit)")
            
            logger.info(f"Found {len(conversations)} unique conversations to process.")
            
            for i, (participants, chat_ids) in enumerate(conversations.items()):
                participant_str = ', '.join(participants)
                logger.info(f"Processing conversation {i+1}/{len(conversations)} with: {participant_str}")
                
                # Fetch all messages for this logical conversation
                messages = self.get_messages_for_conversation(chat_ids)
                if not messages:
                    continue
                
                turns = self.group_messages_into_turns(messages)
                examples = self.create_training_examples(turns)
                
                if examples:
                    all_examples.extend(examples)
                    logger.info(f"  -> Generated {len(examples)} examples from this conversation.")
            
            logger.info(f"\nTotal training examples generated: {len(all_examples)}")
            return all_examples
            
        finally:
            self.close_connection()
    
    def save_to_csv(self, examples: List[Tuple[str, str]], output_path: str = "training_data.csv"):
        """
        Save training examples to CSV file.
        
        Args:
            examples: List of (input, output) pairs
            output_path: Path to save the CSV file
        """
        df = pd.DataFrame(examples, columns=['input', 'output'])
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(examples)} training examples to {output_path}")
        
        # Print some statistics
        logger.info(f"Dataset statistics:")
        logger.info(f"  Total examples: {len(examples)}")
        logger.info(f"  Average input length: {df['input'].str.len().mean():.1f} characters")
        logger.info(f"  Average output length: {df['output'].str.len().mean():.1f} characters")
        logger.info(f"  Input length range: {df['input'].str.len().min()}-{df['input'].str.len().max()} characters")
        logger.info(f"  Output length range: {df['output'].str.len().min()}-{df['output'].str.len().max()} characters")


def main():
    """Main function to run the iMessage processing pipeline."""
    processor = iMessageProcessor()
    
    logger.info("Starting iMessage data processing with new conversation logic...")
    examples = processor.process_all_conversations()
    
    if examples:
        processor.save_to_csv(examples)
        logger.info("Processing completed successfully!")
    else:
        logger.error("No training examples were generated. Check logs for details.")


if __name__ == "__main__":
    main() 
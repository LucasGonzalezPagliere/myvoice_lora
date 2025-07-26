#!/usr/bin/env python3
"""
Debug script to explore the iMessage database and understand the data structure.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from config import DAYS_BACK

def convert_messages_timestamp(timestamp):
    """Convert Messages.app timestamp to Python datetime."""
    try:
        # Messages.app uses nanoseconds since 2001-01-01 00:00:00 UTC
        # Convert to seconds and add the 2001 epoch offset
        unix_timestamp = (timestamp / 1_000_000_000) + 978307200
        return datetime.fromtimestamp(unix_timestamp)
    except (OSError, ValueError):
        # Handle invalid timestamps
        return datetime.now()

def main():
    print("🔍 Debugging iMessage Database Contents\n")
    
    # Connect to database
    home = Path.home()
    db_path = home / "Library" / "Messages" / "chat.db"
    
    print(f"Database path: {db_path}")
    print(f"Days back setting: {DAYS_BACK}")
    
    if DAYS_BACK is not None:
        cutoff_date = datetime.now() - timedelta(days=DAYS_BACK)
        cutoff_timestamp = int((cutoff_date.timestamp() - 978307200) * 1_000_000_000)
        print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Cutoff timestamp: {cutoff_timestamp}")
    else:
        cutoff_date = None
        cutoff_timestamp = None
        print("No date cutoff - processing all history")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get total number of chats
        cursor.execute("SELECT COUNT(*) FROM chat")
        total_chats = cursor.fetchone()[0]
        print(f"\n📊 Total chats in database: {total_chats}")
        
        # Get total number of messages
        cursor.execute("SELECT COUNT(*) FROM message")
        total_messages = cursor.fetchone()[0]
        print(f"📊 Total messages in database: {total_messages}")
        
        # Get messages from you
        cursor.execute("SELECT COUNT(*) FROM message WHERE is_from_me = 1")
        messages_from_you = cursor.fetchone()[0]
        print(f"📊 Messages from you: {messages_from_you}")
        
        # Get recent messages (last 7 days regardless of DAYS_BACK setting)
        week_ago = datetime.now() - timedelta(days=7)
        week_ago_timestamp = int((week_ago.timestamp() - 978307200) * 1_000_000_000)
        
        cursor.execute("SELECT COUNT(*) FROM message WHERE date >= ?", (week_ago_timestamp,))
        recent_messages = cursor.fetchone()[0]
        print(f"📊 Messages in last 7 days: {recent_messages}")
        
        # Get recent messages from you
        cursor.execute("SELECT COUNT(*) FROM message WHERE is_from_me = 1 AND date >= ?", (week_ago_timestamp,))
        recent_from_you = cursor.fetchone()[0]
        print(f"📊 Messages from you in last 7 days: {recent_from_you}")
        
        # Check specific date range if DAYS_BACK is set
        if cutoff_timestamp:
            cursor.execute("SELECT COUNT(*) FROM message WHERE date >= ?", (cutoff_timestamp,))
            filtered_messages = cursor.fetchone()[0]
            print(f"📊 Messages in configured date range: {filtered_messages}")
            
            cursor.execute("SELECT COUNT(*) FROM message WHERE is_from_me = 1 AND date >= ?", (cutoff_timestamp,))
            filtered_from_you = cursor.fetchone()[0]
            print(f"📊 Messages from you in configured date range: {filtered_from_you}")
        
        # Show some sample chats
        print(f"\n📱 Sample chats:")
        cursor.execute("""
            SELECT c.ROWID, c.display_name, c.chat_identifier, 
                   COUNT(cmj.message_id) as message_count
            FROM chat c
            LEFT JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
            GROUP BY c.ROWID
            ORDER BY message_count DESC
            LIMIT 5
        """)
        
        chats = cursor.fetchall()
        for chat_id, display_name, chat_identifier, message_count in chats:
            print(f"  Chat {chat_id}: {display_name or chat_identifier} ({message_count} messages)")
        
        # Show recent messages with details
        print(f"\n💬 Recent messages (last 10):")
        cursor.execute("""
            SELECT m.ROWID, m.text, m.is_from_me, m.date, 
                   h.uncanonicalized_id as phone_number
            FROM message m
            LEFT JOIN handle h ON m.handle_id = h.ROWID
            ORDER BY m.date DESC
            LIMIT 10
        """)
        
        messages = cursor.fetchall()
        for msg_id, text, is_from_me, date, phone in messages:
            msg_date = convert_messages_timestamp(date)
            sender = "YOU" if is_from_me else f"Other ({phone})"
            text_preview = text[:50] + "..." if text and len(text) > 50 else text
            print(f"  {msg_date.strftime('%Y-%m-%d %H:%M')} | {sender}: {text_preview}")
        
        # Check for messages with text content
        print(f"\n📝 Text content analysis:")
        cursor.execute("SELECT COUNT(*) FROM message WHERE text IS NOT NULL AND text != ''")
        with_text = cursor.fetchone()[0]
        print(f"  Messages with text content: {with_text}")
        
        cursor.execute("SELECT COUNT(*) FROM message WHERE text IS NULL OR text = ''")
        without_text = cursor.fetchone()[0]
        print(f"  Messages without text content: {without_text}")
        
        # Check attributedBody content
        cursor.execute("SELECT COUNT(*) FROM message WHERE attributedBody IS NOT NULL")
        with_attributed = cursor.fetchone()[0]
        print(f"  Messages with attributedBody: {with_attributed}")
        
        conn.close()
        
        print(f"\n💡 Recommendations:")
        if filtered_from_you == 0 and DAYS_BACK is not None:
            print("  - No messages from you in the configured date range")
            print("  - Try increasing DAYS_BACK in config.py")
            print("  - Or set DAYS_BACK = None to process all history")
        
        if recent_from_you == 0:
            print("  - No messages from you in the last 7 days")
            print("  - Check if you have sent any iMessages recently")
        
        if total_messages == 0:
            print("  - No messages found in database")
            print("  - Check if you have any iMessage conversations")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 
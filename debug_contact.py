#!/usr/bin/env python3
"""
Debug script to find all chat threads for a specific contact and check their last message date.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

def convert_messages_timestamp(timestamp):
    """Convert Messages.app timestamp to Python datetime."""
    if timestamp is None:
        return None
    try:
        # Messages.app uses nanoseconds since 2001-01-01 00:00:00 UTC
        unix_timestamp = (timestamp / 1_000_000_000) + 978307200
        return datetime.fromtimestamp(unix_timestamp)
    except (OSError, ValueError):
        return None # Return None on error

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_contact.py '<phone_number_or_email>'")
        print("Example: python debug_contact.py '+13054092382'")
        print("\nNote: The contact ID must be in quotes and include the country code (e.g., +1).")
        sys.exit(1)

    contact_id = sys.argv[1]
    print(f"🔍 Debugging history for contact: {contact_id}\n")

    # Connect to db
    home = Path.home()
    db_path = home / "Library" / "Messages" / "chat.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 1. Find the handle_id for the contact
        cursor.execute("SELECT ROWID, id FROM handle WHERE id = ?", (contact_id,))
        handle_result = cursor.fetchall()

        if not handle_result:
            print(f"❌ No handle found for '{contact_id}'. Make sure it's in E.164 format (e.g., +11234567890).")
            conn.close()
            return

        print(f"✅ Found {len(handle_result)} handle(s) for '{contact_id}':")
        for row_id, handle_id_str in handle_result:
            print(f"  - Handle ROWID: {row_id}, ID: {handle_id_str}")

        handle_row_ids = [r[0] for r in handle_result]

        # 2. Find all chat_ids associated with these handles
        print("\n🔎 Finding all associated chat threads...")
        
        placeholders = ','.join('?' for _ in handle_row_ids)
        query = f"""
            SELECT DISTINCT chj.chat_id
            FROM chat_handle_join chj
            WHERE chj.handle_id IN ({placeholders})
        """
        
        cursor.execute(query, handle_row_ids)
        chat_ids = [row[0] for row in cursor.fetchall()]

        if not chat_ids:
            print("❌ No chats found for this contact.")
            conn.close()
            return
            
        print(f"✅ Found {len(chat_ids)} associated chat thread(s): {chat_ids}")

        # 3. For each chat_id, find the last message date
        print("\n🕒 Checking last message date for each thread...")
        
        for chat_id in chat_ids:
            cursor.execute("""
                SELECT MAX(m.date), c.display_name, c.chat_identifier
                FROM message m
                JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                JOIN chat c ON cmj.chat_id = c.ROWID
                WHERE cmj.chat_id = ?
            """, (chat_id,))
            
            result = cursor.fetchone()
            max_date, display_name, chat_identifier = result
            
            last_message_time = convert_messages_timestamp(max_date)
            
            if last_message_time:
                print(f"  - Chat ID: {chat_id} ('{display_name or chat_identifier}')")
                print(f"    Last Message: {last_message_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"  - Chat ID: {chat_id} ('{display_name or chat_identifier}') has no messages or a bad date.")

        conn.close()
        
        print("\n💡 Analysis:")
        print("If you see multiple chat IDs with different last message dates, it confirms that")
        print("your conversation history with this contact is split across multiple threads.")
        print("The current script processes chats one-by-one and might be picking up old,")
        print("inactive threads first.")
    
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main() 
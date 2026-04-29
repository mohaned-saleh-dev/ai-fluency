#!/usr/bin/env python3
"""
Slack Thread Manager - Review and organize Slack threads.

This script:
1. Fetches all threads from Slack conversations
2. Identifies important threads vs old/unimportant ones
3. Marks old/unimportant threads as read
4. Reports important threads with links
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_USER_TOKEN")
DAYS_OLD_THRESHOLD = 30  # Threads older than this are considered "old"
IMPORTANT_KEYWORDS = [
    "urgent", "important", "action required", "deadline", "blocking",
    "critical", "priority", "asap", "p0", "p1", "escalation", "bug",
    "production", "incident", "outage", "security"
]


class SlackThreadManager:
    def __init__(self, token: str):
        """Initialize Slack client."""
        if not token:
            raise ValueError(
                "Slack token not found. Please set SLACK_BOT_TOKEN or SLACK_USER_TOKEN environment variable.\n"
                "You can get a token from: https://api.slack.com/apps -> Your App -> OAuth & Permissions"
            )
        self.client = WebClient(token=token)
        self.user_id = None
        self.important_threads = []
        self.marked_read_count = 0
        
    def get_user_id(self) -> str:
        """Get the current user's ID."""
        if not self.user_id:
            try:
                response = self.client.auth_test()
                self.user_id = response["user_id"]
                print(f"✓ Authenticated as: {response['user']} ({response['user_id']})")
            except SlackApiError as e:
                print(f"❌ Error authenticating: {e.response['error']}")
                sys.exit(1)
        return self.user_id
    
    def get_conversations(self) -> List[Dict]:
        """Get all conversations (channels, DMs, groups) the user is part of."""
        print("\n📋 Fetching conversations...")
        conversations = []
        cursor = None
        
        try:
            while True:
                response = self.client.conversations_list(
                    types="public_channel,private_channel,im,mpim",
                    exclude_archived=True,
                    cursor=cursor,
                    limit=200
                )
                
                conversations.extend(response["channels"])
                
                if not response.get("response_metadata", {}).get("next_cursor"):
                    break
                cursor = response["response_metadata"]["next_cursor"]
                
            print(f"✓ Found {len(conversations)} conversations")
            return conversations
            
        except SlackApiError as e:
            print(f"❌ Error fetching conversations: {e.response['error']}")
            return []
    
    def get_threads_from_conversation(self, channel_id: str, channel_name: str) -> List[Dict]:
        """Get all threads from a conversation."""
        threads = []
        cursor = None
        cutoff_date = datetime.now() - timedelta(days=365)  # Look back 1 year
        
        try:
            while True:
                response = self.client.conversations_history(
                    channel=channel_id,
                    cursor=cursor,
                    limit=200,
                    oldest=str(int(cutoff_date.timestamp()))
                )
                
                messages = response.get("messages", [])
                
                # Find messages with thread replies
                for message in messages:
                    if message.get("thread_ts"):  # This is a reply in a thread
                        continue
                    if message.get("reply_count", 0) > 0:  # This message has replies
                        thread_ts = message.get("ts")
                        threads.append({
                            "channel_id": channel_id,
                            "channel_name": channel_name,
                            "thread_ts": thread_ts,
                            "message_ts": message.get("ts"),
                            "text": message.get("text", ""),
                            "user": message.get("user", ""),
                            "timestamp": float(message.get("ts", 0)),
                            "reply_count": message.get("reply_count", 0),
                            "unread_count": message.get("unread_count", 0),
                            "permalink": None
                        })
                
                if not response.get("response_metadata", {}).get("next_cursor"):
                    break
                cursor = response["response_metadata"]["next_cursor"]
                
        except SlackApiError as e:
            if e.response["error"] != "channel_not_found":
                print(f"⚠️  Error fetching threads from {channel_name}: {e.response['error']}")
        
        return threads
    
    def get_thread_permalink(self, channel_id: str, thread_ts: str) -> Optional[str]:
        """Get permalink for a thread."""
        try:
            response = self.client.chat_getPermalink(
                channel=channel_id,
                message_ts=thread_ts
            )
            return response.get("permalink")
        except SlackApiError:
            return None
    
    def is_important(self, thread: Dict) -> bool:
        """Determine if a thread is important."""
        text = thread.get("text", "").lower()
        timestamp = thread.get("timestamp", 0)
        thread_date = datetime.fromtimestamp(timestamp)
        days_old = (datetime.now() - thread_date).days
        
        # Check if thread is too old
        if days_old > DAYS_OLD_THRESHOLD:
            return False
        
        # Check for important keywords
        for keyword in IMPORTANT_KEYWORDS:
            if keyword in text:
                return True
        
        # Check if user is mentioned (if we can determine that)
        user_id = self.get_user_id()
        if f"<@{user_id}>" in thread.get("text", ""):
            return True
        
        # Recent threads with high engagement might be important
        if days_old <= 7 and thread.get("reply_count", 0) >= 3:
            return True
        
        return False
    
    def mark_thread_as_read(self, channel_id: str, thread_ts: str) -> bool:
        """Mark a thread as read."""
        try:
            # Mark the channel as read up to the thread timestamp
            # This requires channels:write, groups:write, im:write, mpim:write scopes
            self.client.conversations_mark(
                channel=channel_id,
                ts=thread_ts
            )
            return True
        except SlackApiError as e:
            error_code = e.response.get("error", "")
            if error_code == "missing_scope":
                # Don't spam errors if we're missing the scope
                return False
            elif error_code not in ["channel_not_found", "invalid_ts", "not_in_channel"]:
                # Only show unexpected errors
                pass
            return False
    
    def process_all_threads(self):
        """Process all threads across all conversations."""
        print("\n🔍 Processing threads...")
        conversations = self.get_conversations()
        all_threads = []
        
        for conv in conversations:
            channel_id = conv["id"]
            channel_name = conv.get("name", conv.get("user", "Unknown"))
            threads = self.get_threads_from_conversation(channel_id, channel_name)
            
            # Get permalinks for all threads
            for thread in threads:
                permalink = self.get_thread_permalink(channel_id, thread["thread_ts"])
                thread["permalink"] = permalink
                all_threads.append(thread)
        
        print(f"✓ Found {len(all_threads)} total threads")
        
        # Categorize threads
        important = []
        to_mark_read = []
        
        for thread in all_threads:
            if self.is_important(thread):
                important.append(thread)
            else:
                to_mark_read.append(thread)
        
        print(f"\n📊 Thread Analysis:")
        print(f"   • Important threads: {len(important)}")
        print(f"   • Old/unimportant threads: {len(to_mark_read)}")
        
        # Mark old/unimportant threads as read
        print(f"\n📖 Marking old/unimportant threads as read...")
        marked_count = 0
        for thread in to_mark_read:
            if self.mark_thread_as_read(thread["channel_id"], thread["thread_ts"]):
                marked_count += 1
        
        self.marked_read_count = marked_count
        if marked_count > 0:
            print(f"✓ Marked {marked_count} threads as read")
        else:
            print(f"⚠️  Could not mark threads as read. You may need:")
            print(f"   - A user OAuth token (not bot token)")
            print(f"   - Additional scopes: channels:write, groups:write, im:write, mpim:write")
            print(f"   - See SLACK_SETUP.md for details")
        
        # Store important threads
        self.important_threads = important
        
        return important
    
    def generate_report(self) -> str:
        """Generate a report of important threads."""
        if not self.important_threads:
            return "No important threads found."
        
        report = f"\n{'='*80}\n"
        report += f"📌 IMPORTANT SLACK THREADS REPORT\n"
        report += f"{'='*80}\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Total important threads: {len(self.important_threads)}\n"
        report += f"Threads marked as read: {self.marked_read_count}\n"
        report += f"{'='*80}\n\n"
        
        # Sort by timestamp (newest first)
        sorted_threads = sorted(
            self.important_threads,
            key=lambda x: x.get("timestamp", 0),
            reverse=True
        )
        
        for i, thread in enumerate(sorted_threads, 1):
            thread_date = datetime.fromtimestamp(thread["timestamp"])
            days_old = (datetime.now() - thread_date).days
            
            report += f"{i}. [{thread['channel_name']}] "
            report += f"({days_old} days ago, {thread.get('reply_count', 0)} replies)\n"
            
            if thread.get("permalink"):
                report += f"   🔗 {thread['permalink']}\n"
            else:
                report += f"   🔗 https://app.slack.com/client/T{thread['channel_id'][:10]}/C{thread['channel_id']}/thread/{thread['channel_id']}-{thread['thread_ts']}\n"
            
            # Show preview of message
            text_preview = thread.get("text", "")[:200]
            if len(thread.get("text", "")) > 200:
                text_preview += "..."
            report += f"   💬 {text_preview}\n"
            report += "\n"
        
        return report


def main():
    """Main execution function."""
    print("🚀 Slack Thread Manager")
    print("=" * 80)
    
    if not SLACK_TOKEN:
        print("\n❌ Error: Slack token not found!")
        print("\nPlease set one of the following environment variables:")
        print("  - SLACK_BOT_TOKEN (for bot tokens)")
        print("  - SLACK_USER_TOKEN (for user OAuth tokens)")
        print("\nTo get a token:")
        print("  1. Go to https://api.slack.com/apps")
        print("  2. Create or select your app")
        print("  3. Go to 'OAuth & Permissions'")
        print("  4. Install to workspace and copy the token")
        print("  5. Set it as: export SLACK_BOT_TOKEN='xoxb-your-token'")
        sys.exit(1)
    
    try:
        manager = SlackThreadManager(SLACK_TOKEN)
        important_threads = manager.process_all_threads()
        
        report = manager.generate_report()
        print(report)
        
        # Save report to file
        report_file = f"slack_important_threads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"\n💾 Report saved to: {report_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


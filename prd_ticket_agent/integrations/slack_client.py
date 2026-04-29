"""
Slack API client for fetching messages, threads, and managing interactions.
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackClient:
    """Client for interacting with Slack API."""
    
    def __init__(self, token: str):
        """
        Initialize Slack client.
        
        Args:
            token: Slack API token (bot token or user OAuth token)
        """
        if not token:
            raise ValueError("Slack token is required")
        self.client = WebClient(token=token)
        self.user_id = None
        self.user_name = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate and get user info."""
        try:
            response = self.client.auth_test()
            self.user_id = response["user_id"]
            self.user_name = response["user"]
        except SlackApiError as e:
            raise ValueError(f"Failed to authenticate with Slack: {e.response.get('error', 'Unknown error')}")
    
    def get_conversations(
        self,
        types: str = "public_channel,private_channel,im,mpim",
        exclude_archived: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations the user is part of.
        
        Args:
            types: Comma-separated list of conversation types
            exclude_archived: Whether to exclude archived conversations
            
        Returns:
            List of conversation dictionaries
        """
        conversations = []
        cursor = None
        
        try:
            while True:
                response = self.client.conversations_list(
                    types=types,
                    exclude_archived=exclude_archived,
                    cursor=cursor,
                    limit=200
                )
                
                conversations.extend(response["channels"])
                
                if not response.get("response_metadata", {}).get("next_cursor"):
                    break
                cursor = response["response_metadata"]["next_cursor"]
                
        except SlackApiError as e:
            print(f"Warning: Error fetching conversations: {e.response.get('error', 'Unknown error')}")
        
        return conversations
    
    def get_unread_threads(
        self,
        max_threads: int = 50,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get unread threads from all conversations.
        
        Args:
            max_threads: Maximum number of threads to return
            days_back: How many days back to look for threads
            
        Returns:
            List of thread dictionaries with unread messages
        """
        all_threads = []
        conversations = self.get_conversations()
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for conv in conversations:
            channel_id = conv["id"]
            channel_name = conv.get("name", conv.get("user", "Unknown"))
            
            try:
                # Get conversation history
                response = self.client.conversations_history(
                    channel=channel_id,
                    limit=100,
                    oldest=str(int(cutoff_date.timestamp()))
                )
                
                messages = response.get("messages", [])
                
                for message in messages:
                    # Skip if this is a thread reply
                    if message.get("thread_ts") and message.get("thread_ts") != message.get("ts"):
                        continue
                    
                    # Check if message has thread replies
                    reply_count = message.get("reply_count", 0)
                    unread_count = message.get("unread_count", 0)
                    
                    if reply_count > 0 and unread_count > 0:
                        thread_ts = message.get("ts")
                        
                        # Get thread replies
                        thread_replies = self.get_thread_replies(channel_id, thread_ts)
                        
                        thread = {
                            "channel_id": channel_id,
                            "channel_name": channel_name,
                            "thread_ts": thread_ts,
                            "message_ts": message.get("ts"),
                            "text": message.get("text", ""),
                            "user": message.get("user", ""),
                            "timestamp": float(message.get("ts", 0)),
                            "reply_count": reply_count,
                            "unread_count": unread_count,
                            "replies": thread_replies,
                            "permalink": self.get_permalink(channel_id, thread_ts)
                        }
                        
                        all_threads.append(thread)
                        
                        if len(all_threads) >= max_threads:
                            return all_threads
                            
            except SlackApiError as e:
                if e.response.get("error") not in ["channel_not_found", "not_in_channel"]:
                    continue
        
        return all_threads
    
    def get_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """
        Get all replies in a thread.
        
        Args:
            channel_id: Channel ID
            thread_ts: Thread timestamp
            
        Returns:
            List of reply messages
        """
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=100
            )
            
            replies = []
            for message in response.get("messages", []):
                # Skip the parent message
                if message.get("ts") == thread_ts:
                    continue
                
                replies.append({
                    "text": message.get("text", ""),
                    "user": message.get("user", ""),
                    "timestamp": float(message.get("ts", 0)),
                    "ts": message.get("ts")
                })
            
            return replies
            
        except SlackApiError:
            return []
    
    def get_permalink(self, channel_id: str, message_ts: str) -> Optional[str]:
        """
        Get permalink for a message/thread.
        
        Args:
            channel_id: Channel ID
            message_ts: Message timestamp
            
        Returns:
            Permalink URL or None
        """
        try:
            response = self.client.chat_getPermalink(
                channel=channel_id,
                message_ts=message_ts
            )
            return response.get("permalink")
        except SlackApiError:
            return None
    
    def get_message_context(
        self,
        channel_id: str,
        message_ts: str,
        context_messages: int = 5
    ) -> Dict[str, Any]:
        """
        Get context around a message (messages before and after).
        
        Args:
            channel_id: Channel ID
            message_ts: Message timestamp
            context_messages: Number of messages before/after to fetch
            
        Returns:
            Dictionary with message and context
        """
        try:
            # Get messages before
            response_before = self.client.conversations_history(
                channel=channel_id,
                latest=message_ts,
                limit=context_messages + 1,
                inclusive=False
            )
            
            # Get messages after
            response_after = self.client.conversations_history(
                channel=channel_id,
                oldest=message_ts,
                limit=context_messages + 1,
                inclusive=False
            )
            
            before_messages = response_before.get("messages", [])
            after_messages = response_after.get("messages", [])
            
            # Get the main message
            response_main = self.client.conversations_history(
                channel=channel_id,
                latest=message_ts,
                limit=1,
                inclusive=True
            )
            main_message = response_main.get("messages", [{}])[0] if response_main.get("messages") else {}
            
            return {
                "main_message": main_message,
                "before": before_messages,
                "after": after_messages
            }
            
        except SlackApiError:
            return {
                "main_message": {},
                "before": [],
                "after": []
            }













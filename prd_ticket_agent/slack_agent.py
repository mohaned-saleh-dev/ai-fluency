"""
Slack Management Agent - AI-powered assistant for managing Slack interactions.
Provides message summaries, context-aware response suggestions, and knowledge integration.
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from .integrations.slack_client import SlackClient
from .integrations.notion_client import NotionClient
from .integrations.gemini_client import GeminiClient
from .config import AgentContext


class SlackManagementAgent:
    """
    AI-powered Slack management agent that:
    - Summarizes Slack messages and threads
    - Suggests context-aware responses using Notion knowledge
    - Integrates with entire Notion workspace for context
    """
    
    def __init__(self, context: AgentContext):
        """
        Initialize the Slack Management Agent.
        
        Args:
            context: Agent context with API keys and configuration
        """
        self.context = context
        self.slack_client = None
        self.notion_client = None
        self.gemini_client = None
        self._initialize_clients()
        self._knowledge_base = None
    
    def _initialize_clients(self):
        """Initialize all required clients."""
        # Initialize Slack client
        slack_token = os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_USER_TOKEN")
        if slack_token:
            self.slack_client = SlackClient(slack_token)
        
        # Initialize Notion client
        if self.context.notion_api_key:
            self.notion_client = NotionClient(self.context.notion_api_key)
        
        # Initialize Gemini client
        if self.context.gemini_api_key:
            self.gemini_client = GeminiClient(
                self.context.gemini_api_key,
                self.context.gemini_model_name
            )
    
    async def load_knowledge_base(self, max_pages: int = 100) -> str:
        """
        Load knowledge base from Notion workspace.
        
        Args:
            max_pages: Maximum number of pages to load
            
        Returns:
            Combined knowledge base text
        """
        if not self.notion_client:
            return ""
        
        if self._knowledge_base is None:
            print("📚 Loading knowledge base from Notion...")
            self._knowledge_base = await self.notion_client.extract_knowledge_base(
                max_pages=max_pages
            )
            print(f"✓ Loaded knowledge base ({len(self._knowledge_base)} characters)")
        
        return self._knowledge_base
    
    async def search_notion_knowledge(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Notion workspace for relevant information.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of relevant pages/databases
        """
        if not self.notion_client:
            return []
        
        try:
            results = await self.notion_client.search_workspace(
                query=query,
                max_results=max_results
            )
            return results
        except Exception as e:
            print(f"Warning: Error searching Notion: {e}")
            return []
    
    async def summarize_thread(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of a Slack thread.
        
        Args:
            thread: Thread dictionary from Slack
            
        Returns:
            Dictionary with summary and key insights
        """
        if not self.gemini_client:
            return {
                "summary": "AI summarization not available (Gemini API key missing)",
                "key_points": [],
                "action_items": [],
                "sentiment": "neutral"
            }
        
        # Build thread content
        thread_content = f"Channel: {thread.get('channel_name', 'Unknown')}\n"
        thread_content += f"Original Message: {thread.get('text', '')}\n\n"
        thread_content += "Replies:\n"
        
        for i, reply in enumerate(thread.get('replies', []), 1):
            thread_content += f"{i}. {reply.get('text', '')}\n"
        
        # Load knowledge base for context
        knowledge_base = await self.load_knowledge_base(max_pages=50)
        
        prompt = f"""Analyze this Slack thread and provide a comprehensive summary.

Thread Content:
{thread_content}

{f'Relevant Knowledge Base Context:\n{knowledge_base[:5000]}\n' if knowledge_base else ''}

Please provide:
1. A concise summary (2-3 sentences)
2. Key points discussed (bullet list)
3. Any action items or decisions made
4. Overall sentiment (positive/neutral/negative/urgent)

Format your response as:
SUMMARY: [summary text]
KEY_POINTS:
- [point 1]
- [point 2]
ACTION_ITEMS:
- [item 1]
- [item 2]
SENTIMENT: [sentiment]
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse response
            summary_data = self._parse_summary_response(response)
            summary_data["raw_summary"] = response
            
            return summary_data
            
        except Exception as e:
            return {
                "summary": f"Error generating summary: {e}",
                "key_points": [],
                "action_items": [],
                "sentiment": "neutral"
            }
    
    def _parse_summary_response(self, response: str) -> Dict[str, Any]:
        """Parse the summary response from Gemini."""
        summary_data = {
            "summary": "",
            "key_points": [],
            "action_items": [],
            "sentiment": "neutral"
        }
        
        lines = response.split("\n")
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("SUMMARY:"):
                summary_data["summary"] = line.replace("SUMMARY:", "").strip()
                current_section = None
            elif line.startswith("KEY_POINTS:"):
                current_section = "key_points"
            elif line.startswith("ACTION_ITEMS:"):
                current_section = "action_items"
            elif line.startswith("SENTIMENT:"):
                summary_data["sentiment"] = line.replace("SENTIMENT:", "").strip().lower()
                current_section = None
            elif current_section and line.startswith("-"):
                summary_data[current_section].append(line[1:].strip())
        
        return summary_data
    
    async def suggest_response(
        self,
        thread: Dict[str, Any],
        user_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest a response to a Slack thread using Notion knowledge.
        
        Args:
            thread: Thread dictionary from Slack
            user_context: Optional additional context about the user's role/preferences
            
        Returns:
            Dictionary with suggested response and reasoning
        """
        if not self.gemini_client:
            return {
                "suggested_response": "AI response suggestions not available (Gemini API key missing)",
                "reasoning": "",
                "tone": "professional"
            }
        
        # Build thread content
        thread_content = f"Channel: {thread.get('channel_name', 'Unknown')}\n"
        thread_content += f"Original Message: {thread.get('text', '')}\n\n"
        thread_content += "Thread Replies:\n"
        
        for i, reply in enumerate(thread.get('replies', []), 1):
            thread_content += f"{i}. {reply.get('text', '')}\n"
        
        # Search Notion for relevant context
        search_query = f"{thread.get('text', '')} {thread.get('channel_name', '')}"
        notion_results = await self.search_notion_knowledge(search_query, max_results=5)
        
        # Extract relevant knowledge
        relevant_knowledge = ""
        if notion_results:
            for result in notion_results[:3]:  # Top 3 results
                page_id = result.get("id")
                if page_id:
                    try:
                        page_content = await self.notion_client.get_page_content(page_id)
                        page_text = self.notion_client.extract_text_from_blocks(
                            page_content.get("blocks", [])
                        )
                        relevant_knowledge += f"\n--- Relevant Document ---\n{page_text[:2000]}\n"
                    except Exception:
                        continue
        
        # Also load general knowledge base
        knowledge_base = await self.load_knowledge_base(max_pages=30)
        
        prompt = f"""You are helping to craft a response to a Slack thread. Use the context provided to suggest an appropriate, helpful response.

Thread Content:
{thread_content}

{f'Relevant Notion Knowledge:\n{relevant_knowledge}\n' if relevant_knowledge else ''}

{f'Additional Knowledge Base Context:\n{knowledge_base[:3000]}\n' if knowledge_base else ''}

{f'User Context:\n{user_context}\n' if user_context else ''}

Please suggest:
1. A response message (2-3 sentences, professional but friendly)
2. Reasoning for why this response is appropriate
3. Suggested tone (professional/friendly/casual/urgent)

Format your response as:
RESPONSE: [suggested response text]
REASONING: [why this response is appropriate]
TONE: [tone]
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=500
            )
            
            # Parse response
            suggestion_data = self._parse_suggestion_response(response)
            suggestion_data["raw_suggestion"] = response
            
            return suggestion_data
            
        except Exception as e:
            return {
                "suggested_response": f"Error generating suggestion: {e}",
                "reasoning": "",
                "tone": "professional"
            }
    
    def _parse_suggestion_response(self, response: str) -> Dict[str, Any]:
        """Parse the suggestion response from Gemini."""
        suggestion_data = {
            "suggested_response": "",
            "reasoning": "",
            "tone": "professional"
        }
        
        lines = response.split("\n")
        current_field = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("RESPONSE:"):
                suggestion_data["suggested_response"] = line.replace("RESPONSE:", "").strip()
                current_field = None
            elif line.startswith("REASONING:"):
                suggestion_data["reasoning"] = line.replace("REASONING:", "").strip()
                current_field = None
            elif line.startswith("TONE:"):
                suggestion_data["tone"] = line.replace("TONE:", "").strip().lower()
                current_field = None
            elif current_field:
                # Continue previous field if multi-line
                suggestion_data[current_field] += " " + line
        
        return suggestion_data
    
    async def process_unread_threads(
        self,
        max_threads: int = 10,
        summarize: bool = True,
        suggest_responses: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process all unread threads with summaries and response suggestions.
        
        Args:
            max_threads: Maximum number of threads to process
            summarize: Whether to generate summaries
            suggest_responses: Whether to suggest responses
            
        Returns:
            List of processed threads with summaries and suggestions
        """
        if not self.slack_client:
            raise ValueError("Slack client not initialized. Please set SLACK_BOT_TOKEN or SLACK_USER_TOKEN.")
        
        print("📬 Fetching unread threads...")
        threads = self.slack_client.get_unread_threads(max_threads=max_threads)
        print(f"✓ Found {len(threads)} unread threads")
        
        processed_threads = []
        
        for i, thread in enumerate(threads, 1):
            print(f"\n📋 Processing thread {i}/{len(threads)}: {thread.get('channel_name')}")
            
            processed_thread = {
                "thread": thread,
                "summary": None,
                "suggestion": None
            }
            
            if summarize:
                print("  📝 Generating summary...")
                processed_thread["summary"] = await self.summarize_thread(thread)
            
            if suggest_responses:
                print("  💡 Generating response suggestion...")
                processed_thread["suggestion"] = await self.suggest_response(thread)
            
            processed_threads.append(processed_thread)
        
        return processed_threads
    
    def format_thread_report(self, processed_threads: List[Dict[str, Any]]) -> str:
        """
        Format processed threads into a readable report.
        
        Args:
            processed_threads: List of processed threads
            
        Returns:
            Formatted report string
        """
        report = f"\n{'='*80}\n"
        report += f"📊 SLACK THREADS REPORT\n"
        report += f"{'='*80}\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Total threads: {len(processed_threads)}\n"
        report += f"{'='*80}\n\n"
        
        for i, processed in enumerate(processed_threads, 1):
            thread = processed["thread"]
            thread_date = datetime.fromtimestamp(thread.get("timestamp", 0))
            
            report += f"{i}. [{thread.get('channel_name', 'Unknown')}] "
            report += f"({thread_date.strftime('%Y-%m-%d %H:%M')}, "
            report += f"{thread.get('reply_count', 0)} replies, "
            report += f"{thread.get('unread_count', 0)} unread)\n"
            
            if thread.get("permalink"):
                report += f"   🔗 {thread['permalink']}\n"
            
            report += f"\n   Original: {thread.get('text', '')[:200]}\n"
            
            if processed.get("summary"):
                summary = processed["summary"]
                report += f"\n   📝 Summary: {summary.get('summary', 'N/A')}\n"
                
                if summary.get("key_points"):
                    report += f"   Key Points:\n"
                    for point in summary["key_points"]:
                        report += f"     • {point}\n"
                
                if summary.get("action_items"):
                    report += f"   Action Items:\n"
                    for item in summary["action_items"]:
                        report += f"     • {item}\n"
                
                report += f"   Sentiment: {summary.get('sentiment', 'neutral')}\n"
            
            if processed.get("suggestion"):
                suggestion = processed["suggestion"]
                report += f"\n   💡 Suggested Response:\n"
                report += f"   {suggestion.get('suggested_response', 'N/A')}\n"
                report += f"   Reasoning: {suggestion.get('reasoning', 'N/A')}\n"
                report += f"   Tone: {suggestion.get('tone', 'professional')}\n"
            
            report += "\n" + "-"*80 + "\n\n"
        
        return report













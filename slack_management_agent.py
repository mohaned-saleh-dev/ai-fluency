#!/usr/bin/env python3
"""
Slack Management Agent - Main CLI
AI-powered assistant for managing Slack interactions with Notion knowledge integration.
"""

import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from prd_ticket_agent.config import load_context_from_env
from prd_ticket_agent.slack_agent import SlackManagementAgent


def print_banner():
    """Print welcome banner."""
    print("\n" + "="*80)
    print("🤖 Slack Management Agent")
    print("="*80)
    print("AI-powered assistant for managing your Slack interactions")
    print("Integrated with your Notion workspace for context-aware responses")
    print("="*80 + "\n")


async def process_threads(agent: SlackManagementAgent, max_threads: int = 10):
    """Process unread threads with summaries and suggestions."""
    print("🚀 Starting thread processing...\n")
    
    try:
        processed_threads = await agent.process_unread_threads(
            max_threads=max_threads,
            summarize=True,
            suggest_responses=True
        )
        
        # Generate report
        report = agent.format_thread_report(processed_threads)
        print(report)
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"slack_threads_report_{timestamp}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"\n💾 Report saved to: {report_file}")
        
        return processed_threads
        
    except Exception as e:
        print(f"\n❌ Error processing threads: {e}")
        import traceback
        traceback.print_exc()
        return []


async def summarize_single_thread(agent: SlackManagementAgent, thread_url: str):
    """Summarize a single thread from URL."""
    print(f"📋 Summarizing thread: {thread_url}\n")
    
    # Extract channel and message timestamp from URL
    # Slack URLs format: https://workspace.slack.com/archives/CHANNEL_ID/pMESSAGE_TS
    # This is a simplified version - in production, you'd parse the URL properly
    
    print("⚠️  Single thread summarization from URL not yet implemented.")
    print("   Please use the 'process' command to summarize all unread threads.")


async def suggest_response_interactive(agent: SlackManagementAgent):
    """Interactive mode for suggesting responses."""
    print("💬 Interactive Response Suggestion Mode")
    print("="*80 + "\n")
    
    if not agent.slack_client:
        print("❌ Slack client not available. Please set SLACK_BOT_TOKEN or SLACK_USER_TOKEN.")
        return
    
    # Get unread threads
    threads = agent.slack_client.get_unread_threads(max_threads=20)
    
    if not threads:
        print("✓ No unread threads found.")
        return
    
    print(f"Found {len(threads)} unread threads:\n")
    
    for i, thread in enumerate(threads, 1):
        thread_date = datetime.fromtimestamp(thread.get("timestamp", 0))
        print(f"{i}. [{thread.get('channel_name', 'Unknown')}] "
              f"({thread_date.strftime('%Y-%m-%d %H:%M')})")
        print(f"   {thread.get('text', '')[:100]}...")
        if thread.get("permalink"):
            print(f"   {thread['permalink']}")
        print()
    
    try:
        choice = input("Enter thread number to get response suggestion (or 'q' to quit): ").strip()
        
        if choice.lower() == 'q':
            return
        
        thread_idx = int(choice) - 1
        if 0 <= thread_idx < len(threads):
            selected_thread = threads[thread_idx]
            
            print(f"\n💡 Generating response suggestion...\n")
            suggestion = await agent.suggest_response(selected_thread)
            
            print("="*80)
            print("SUGGESTED RESPONSE:")
            print("="*80)
            print(suggestion.get("suggested_response", "N/A"))
            print("\nREASONING:")
            print(suggestion.get("reasoning", "N/A"))
            print(f"\nTONE: {suggestion.get('tone', 'professional')}")
            print("="*80 + "\n")
        else:
            print("❌ Invalid thread number.")
    except ValueError:
        print("❌ Invalid input. Please enter a number.")
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Slack Management Agent - AI-powered Slack assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all unread threads (default: 10 threads)
  python slack_management_agent.py process

  # Process specific number of threads
  python slack_management_agent.py process --max-threads 20

  # Interactive response suggestion mode
  python slack_management_agent.py suggest

  # Summarize a single thread (from URL)
  python slack_management_agent.py summarize --url <thread_url>
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process unread threads")
    process_parser.add_argument(
        "--max-threads",
        type=int,
        default=10,
        help="Maximum number of threads to process (default: 10)"
    )
    
    # Suggest command
    suggest_parser = subparsers.add_parser("suggest", help="Interactive response suggestion")
    
    # Summarize command
    summarize_parser = subparsers.add_parser("summarize", help="Summarize a single thread")
    summarize_parser.add_argument("--url", type=str, help="Thread URL to summarize")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print_banner()
    
    # Load context
    try:
        context = load_context_from_env()
        
        # Check required credentials
        slack_token = os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_USER_TOKEN")
        if not slack_token:
            print("❌ Error: Slack token not found!")
            print("\nPlease set one of the following environment variables:")
            print("  - SLACK_BOT_TOKEN (for bot tokens)")
            print("  - SLACK_USER_TOKEN (for user OAuth tokens)")
            print("\nSee SLACK_SETUP.md for instructions.")
            sys.exit(1)
        
        if not context.gemini_api_key:
            print("⚠️  Warning: Gemini API key not found.")
            print("   Summarization and response suggestions will be limited.")
            print("   Set GEMINI_API_KEY environment variable for full functionality.")
        
        if not context.notion_api_key:
            print("⚠️  Warning: Notion API key not found.")
            print("   Knowledge base integration will be disabled.")
            print("   Set NOTION_API_KEY environment variable for full functionality.")
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)
    
    # Initialize agent
    try:
        agent = SlackManagementAgent(context)
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        sys.exit(1)
    
    # Execute command
    if args.command == "process":
        asyncio.run(process_threads(agent, max_threads=args.max_threads))
    elif args.command == "suggest":
        asyncio.run(suggest_response_interactive(agent))
    elif args.command == "summarize":
        if args.url:
            asyncio.run(summarize_single_thread(agent, args.url))
        else:
            print("❌ Error: --url is required for summarize command")
            sys.exit(1)


if __name__ == "__main__":
    import os
    main()













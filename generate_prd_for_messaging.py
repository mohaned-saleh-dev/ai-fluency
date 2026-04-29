#!/usr/bin/env python3
"""
Generate PRD for In-App Customer Messaging Inbox initiative.
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from prd_ticket_agent import PRDTicketAgent, AgentContext
from prd_ticket_agent.config import load_context_from_env


async def generate_prd():
    """Generate the PRD for the messaging inbox initiative."""
    # Load context
    context = load_context_from_env()
    
    # Initialize agent
    agent = PRDTicketAgent(context)
    
    # Comprehensive project description
    project_description = """
    Build an in-app Customer Messaging Inbox to replace email as the primary async communication channel between customers and Tamara, and to embed live chat conversations and support ticket updates in one unified experience.

    End state UX: similar to Airbnb's Messages tab, which acts as a single inbox for conversations (including support) with clear threads, search, and a consistent place to follow up.

    Core components (Phase 1):
    - Support Inbox (async messaging): customers can message Tamara from the app, receive replies asynchronously, and continue the same thread over days/weeks (instead of email).
    - Multi-threaded conversations: Multiple chat threads (e.g., "Refund follow-up", "Order issue", "Account issue"), so customers don't lose context or mix topics.
    - Ticket updates inside the thread: whenever a support ticket is created/updated/resolved, the customer sees status updates as timeline events/messages (e.g., "Ticket created", "Assigned", "Awaiting info", "Resolved").

    Why: Email-based support is fragmented: customers lose context, replies are slow, and threads are hard to track across devices. In-app messaging gives a single, persistent place for customers to contact support, get chatbot help, track progress of open issues, and continue the conversation without starting over. This should reduce repeat contacts and improve perceived transparency.

    Target audience: all customers who currently contact Tamara via email for support follow-ups, updates, clarifications, and document sharing.

    Related work: Another team is building the messaging and notification center. This PRD should align with that work and reference it where relevant.
    """
    
    # Additional context
    additional_context = {
        'related_prd_url': 'https://www.notion.so/tamaracom/PRD-Unified-in-app-messaging-AI-sidekick-for-Q1-2026-2aa62429127880769e6dc4e481985a5a',
        'phase': 'Phase 1',
        'target_quarter': 'Q1 2026',
        'reference_ux': 'Airbnb Messages tab',
        'key_requirements': [
            'Replace email as primary async communication channel',
            'Unified inbox for all customer-Tamara communications',
            'Persistent multi-threaded conversations',
            'Embed ticket updates in threads',
            'Async messaging support',
            'AI-powered thread titling',
            'Search functionality',
            'Cross-device persistence'
        ],
        'success_metrics_focus': [
            'Reduce repeat contacts',
            'Improve customer satisfaction',
            'Increase chatbot containment',
            'Reduce email support volume',
            'Improve response time perception'
        ]
    }
    
    print("Generating comprehensive PRD...")
    print("This may take a minute as we gather context and generate content...\n")
    
    prd = await agent.create_prd(
        project_description=project_description,
        additional_context=additional_context
    )
    
    return prd


if __name__ == "__main__":
    try:
        result = asyncio.run(generate_prd())
        
        print("\n" + "="*80)
        print("PRD Generated Successfully!")
        print("="*80)
        print(f"\nReferences used: {', '.join(result['metadata']['references_used'])}")
        
        # Save to JSON
        output_file = Path("prd_messaging_inbox.json")
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✅ PRD saved to: {output_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("PRD Content Summary:")
        print("="*80)
        for section, content in result['content'].items():
            if content:
                preview = str(content)[:200] + "..." if len(str(content)) > 200 else str(content)
                print(f"\n{section.replace('_', ' ').title()}:")
                print(f"  {preview}")
        
    except Exception as e:
        print(f"\n❌ Error generating PRD: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




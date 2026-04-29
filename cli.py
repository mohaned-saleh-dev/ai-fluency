#!/usr/bin/env python3
"""
Command-line interface for the PRD and Ticket Writing Agent.

This is a focused agent dedicated to creating Product Requirements Documents (PRDs)
and Jira tickets using Gemini AI, Notion, and Jira integrations.
"""

import asyncio
import argparse
import json
import sys
from prd_ticket_agent import PRDTicketAgent, AgentContext
from prd_ticket_agent.config import load_context_from_env, load_context_from_file


async def create_prd(args):
    """Create a PRD."""
    try:
        # Load context
        if args.config:
            context = load_context_from_file(args.config)
        else:
            context = load_context_from_env()
        
        # Validate required configuration
        if not context.gemini_api_key:
            print("Error: GEMINI_API_KEY is required. Set it as an environment variable or in config.json")
            sys.exit(1)
        
        # Initialize agent
        print("🚀 Initializing PRD Ticket Agent...")
        agent = PRDTicketAgent(context)
        
        # Read project description
        if args.description:
            project_description = args.description
        elif args.file:
            try:
                with open(args.file, 'r') as f:
                    project_description = f.read()
            except FileNotFoundError:
                print(f"Error: File not found: {args.file}")
                sys.exit(1)
        else:
            print("Error: Please provide either --description or --file")
            sys.exit(1)
        
        # Create PRD
        print("📝 Creating PRD...")
        prd = await agent.create_prd(
            project_description=project_description,
            additional_context={"output_format": args.format}
        )
        
        # Output result
        if args.format == "json":
            print(json.dumps(prd, indent=2))
        else:
            print("\n" + "="*80)
            print("✅ PRD Generated Successfully")
            print("="*80)
            if prd.get('metadata', {}).get('references_used'):
                print(f"\n📚 References used: {', '.join(prd['metadata']['references_used'])}")
            print("\n📄 Content:")
            for section, content in prd.get('content', {}).items():
                print(f"\n{section.upper().replace('_', ' ')}:")
                if isinstance(content, list):
                    for item in content:
                        print(f"  - {item}")
                else:
                    print(f"  {content}")
    except Exception as e:
        print(f"❌ Error creating PRD: {e}")
        sys.exit(1)


async def create_ticket(args):
    """Create a Jira ticket."""
    try:
        # Load context
        if args.config:
            context = load_context_from_file(args.config)
        else:
            context = load_context_from_env()
        
        # Validate required configuration
        if not context.gemini_api_key:
            print("Error: GEMINI_API_KEY is required. Set it as an environment variable or in config.json")
            sys.exit(1)
        
        # Initialize agent
        print("🚀 Initializing PRD Ticket Agent...")
        agent = PRDTicketAgent(context)
        
        # Get PRD content if provided
        prd_content = None
        if args.prd_file:
            try:
                with open(args.prd_file, 'r') as f:
                    prd_content = json.load(f)
            except FileNotFoundError:
                print(f"Error: File not found: {args.prd_file}")
                sys.exit(1)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in file: {args.prd_file}")
                sys.exit(1)
        
        # Create ticket
        print("🎫 Creating Jira ticket...")
        ticket = await agent.create_ticket(
            prd_id=args.prd_id,
            prd_content=prd_content,
            ticket_description=args.description,
            project_key=args.project
        )
        
        # Output result
        if args.format == "json":
            print(json.dumps(ticket, indent=2))
        else:
            print("\n" + "="*80)
            print("✅ Ticket Generated Successfully")
            print("="*80)
            if ticket.get('metadata', {}).get('references_used'):
                print(f"\n📚 References used: {', '.join(ticket['metadata']['references_used'])}")
            print("\n📄 Content:")
            print(f"\n🧑‍💻 User Story:")
            print(f"  {ticket.get('content', {}).get('user_story', 'N/A')}")
            print(f"\n✅ Acceptance Criteria:")
            for ac in ticket.get('content', {}).get('acceptance_criteria', []):
                print(f"  - {ac}")
            print(f"\n📝 Description:")
            print(f"  {ticket.get('content', {}).get('description', 'N/A')}")
            
            if ticket.get('jira_issue'):
                print(f"\n🔗 Jira Issue Created: {ticket['jira_issue'].get('key')}")
                if ticket['jira_issue'].get('url'):
                    print(f"   URL: {ticket['jira_issue']['url']}")
    except Exception as e:
        print(f"❌ Error creating ticket: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PRD and Jira Ticket Writing Agent - Create PRDs and Jira tickets using AI",
        epilog="For more information, see README.md"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # PRD creation command
    prd_parser = subparsers.add_parser('prd', help='Create a PRD')
    prd_parser.add_argument(
        '--description', '-d',
        help='Project description'
    )
    prd_parser.add_argument(
        '--file', '-f',
        help='File containing project description'
    )
    prd_parser.add_argument(
        '--config', '-c',
        help='Path to configuration file (default: use environment variables)'
    )
    prd_parser.add_argument(
        '--format',
        choices=['json', 'text'],
        default='text',
        help='Output format'
    )
    
    # Ticket creation command
    ticket_parser = subparsers.add_parser('ticket', help='Create a Jira ticket')
    ticket_parser.add_argument(
        '--prd-id',
        help='Notion PRD page ID'
    )
    ticket_parser.add_argument(
        '--prd-file',
        help='Path to PRD JSON file'
    )
    ticket_parser.add_argument(
        '--description', '-d',
        help='Ticket description'
    )
    ticket_parser.add_argument(
        '--project', '-p',
        required=True,
        help='Jira project key'
    )
    ticket_parser.add_argument(
        '--config', '-c',
        help='Path to configuration file (default: use environment variables)'
    )
    ticket_parser.add_argument(
        '--format',
        choices=['json', 'text'],
        default='text',
        help='Output format'
    )
    
    args = parser.parse_args()
    
    if args.command == 'prd':
        asyncio.run(create_prd(args))
    elif args.command == 'ticket':
        asyncio.run(create_ticket(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()




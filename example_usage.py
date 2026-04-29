"""
Example usage of the PRD and Ticket Writing Agent.
"""

import asyncio
from prd_ticket_agent import PRDTicketAgent, AgentContext
from prd_ticket_agent.config import load_context_from_env


async def example_create_prd():
    """Example: Create a PRD."""
    # Load context from environment variables
    context = load_context_from_env()
    
    # Initialize agent
    agent = PRDTicketAgent(context)
    
    # Create PRD
    project_description = """
    We need to add a feature that allows users to save their favorite items
    for later viewing. Users should be able to create collections of items
    and share them with others.
    """
    
    prd = await agent.create_prd(
        project_description=project_description,
        additional_context={
            "priority": "high",
            "target_release": "Q2 2025"
        }
    )
    
    print("PRD Created!")
    print(f"References used: {prd['metadata']['references_used']}")
    print("\nPRD Content:")
    for section, content in prd['content'].items():
        print(f"\n{section}:")
        print(content)


async def example_create_ticket():
    """Example: Create a Jira ticket."""
    # Load context
    context = load_context_from_env()
    
    # Initialize agent
    agent = PRDTicketAgent(context)
    
    # Create ticket linked to a PRD
    ticket = await agent.create_ticket(
        prd_id="notion_page_id_here",  # Replace with actual Notion page ID
        ticket_description="Implement the UI for the favorites feature",
        project_key="PROJ"  # Replace with your Jira project key
    )
    
    print("Ticket Created!")
    print(f"References used: {ticket['metadata']['references_used']}")
    print("\nTicket Content:")
    print(f"User Story: {ticket['content']['user_story']}")
    print(f"\nAcceptance Criteria:")
    for ac in ticket['content']['acceptance_criteria']:
        print(f"  - {ac}")
    
    if ticket.get('jira_issue'):
        print(f"\nJira Issue: {ticket['jira_issue'].get('key')}")


async def example_with_custom_context():
    """Example: Using custom context."""
    # Create custom context
    context = AgentContext(
        notion_api_key="your_notion_api_key",
        jira_url="https://your-company.atlassian.net",
        jira_email="your_email@company.com",
        jira_api_token="your_jira_api_token",
        notion_all_prds_page_id="your_all_prds_page_id",
        notion_all_tickets_page_id="your_all_tickets_page_id",
        notion_squad_priorities_page_id="your_squad_priorities_page_id"
    )
    
    agent = PRDTicketAgent(context)
    
    # Get context from Notion
    notion_context = await agent.get_context_from_notion()
    print(f"Retrieved context from Notion:")
    print(f"  - Squad priorities: {'Yes' if notion_context.get('squad_priorities') else 'No'}")
    print(f"  - All PRDs: {'Yes' if notion_context.get('all_prds') else 'No'}")
    print(f"  - All Tickets: {len(notion_context.get('all_tickets', []))} tickets")


if __name__ == "__main__":
    print("Example 1: Create PRD")
    print("-" * 50)
    # Uncomment to run:
    # asyncio.run(example_create_prd())
    
    print("\nExample 2: Create Ticket")
    print("-" * 50)
    # Uncomment to run:
    # asyncio.run(example_create_ticket())
    
    print("\nExample 3: Custom Context")
    print("-" * 50)
    # Uncomment to run:
    # asyncio.run(example_with_custom_context())




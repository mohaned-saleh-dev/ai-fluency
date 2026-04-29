#!/usr/bin/env python3
"""
Delete all epics under an initiative and create a single new epic
that captures the essence based on Notion context.
"""

import asyncio
import sys
import warnings
from pathlib import Path
from typing import List, Dict, Any

# Suppress warnings
warnings.filterwarnings('ignore', category=FutureWarning)

sys.path.insert(0, str(Path(__file__).parent))

from prd_ticket_agent import PRDTicketAgent
from prd_ticket_agent.config import load_context_from_env
from prd_ticket_agent.integrations.jira_client import JiraClient
from prd_ticket_agent.integrations.gemini_client import GeminiClient


def extract_text_from_adf(adf_content: Any) -> str:
    """Extract plain text from Jira ADF (Atlassian Document Format)."""
    if not isinstance(adf_content, dict):
        return str(adf_content)
    
    text_parts = []
    content = adf_content.get('content', [])
    
    for item in content:
        if isinstance(item, dict):
            item_type = item.get('type', '')
            
            if item_type == 'heading':
                level = item.get('attrs', {}).get('level', 1)
                para = item.get('content', [])
                heading_text = ""
                for p in para:
                    if isinstance(p, dict) and p.get('type') == 'text':
                        heading_text += p.get('text', '')
                if heading_text:
                    text_parts.append(f"\n{'#' * level} {heading_text}\n")
            
            elif item_type == 'paragraph':
                para = item.get('content', [])
                para_text = ""
                for p in para:
                    if isinstance(p, dict):
                        if p.get('type') == 'text':
                            para_text += p.get('text', '')
                        elif p.get('type') == 'hardBreak':
                            para_text += '\n'
                if para_text:
                    text_parts.append(para_text)
            
            elif item_type == 'bulletList' or item_type == 'orderedList':
                list_items = item.get('content', [])
                for li in list_items:
                    li_content = li.get('content', [])
                    for li_item in li_content:
                        if li_item.get('type') == 'paragraph':
                            para = li_item.get('content', [])
                            item_text = ""
                            for p in para:
                                if isinstance(p, dict) and p.get('type') == 'text':
                                    item_text += p.get('text', '')
                            if item_text:
                                text_parts.append(f"- {item_text}")
    
    return '\n'.join(text_parts)


async def recreate_epic(initiative_key: str, epic_keys_to_delete: List[str] = None):
    """Delete old epics and create a new one based on initiative and Notion context."""
    print(f"🚀 Recreating Epic for Initiative: {initiative_key}\n")
    
    # Load context
    context = load_context_from_env()
    
    if not context.gemini_api_key:
        print("❌ Error: GEMINI_API_KEY required")
        return
    
    if not context.jira_url or not context.jira_api_token:
        print("❌ Error: Jira credentials required")
        return
    
    # Initialize clients
    jira_client = JiraClient(context.jira_url, context.jira_email, context.jira_api_token)
    gemini_client = GeminiClient(context.gemini_api_key, context.gemini_model_name)
    
    # Initialize agent for Notion context
    agent = PRDTicketAgent(context)
    
    # Get initiative
    print(f"📋 Fetching initiative {initiative_key}...")
    try:
        initiative = await jira_client.get_issue(initiative_key)
        fields = initiative.get('fields', {})
        initiative_summary = fields.get('summary', 'N/A')
        initiative_desc = fields.get('description', {})
        
        # Extract description text
        initiative_desc_text = extract_text_from_adf(initiative_desc) if isinstance(initiative_desc, dict) else str(initiative_desc)
        
        print(f"✅ Found: {initiative_summary}")
        print(f"   Description: {initiative_desc_text[:200]}...\n")
        
        # Get project key from initiative
        project_key = fields.get('project', {}).get('key', 'CSSV')
        
    except Exception as e:
        print(f"❌ Error fetching initiative: {e}")
        return
    
    # Get Notion context
    print("📚 Gathering Notion context...")
    notion_context = {}
    if agent.notion_client:
        from prd_ticket_agent.prd_generator import PRDGenerator
        generator = PRDGenerator(agent.notion_client, context, jira_client)
        notion_context = await generator._gather_notion_context()
        print(f"✅ Loaded Notion context\n")
    
    # Delete old epics if provided
    if epic_keys_to_delete:
        print(f"🗑️  Deleting {len(epic_keys_to_delete)} old epics...")
        for epic_key in epic_keys_to_delete:
            try:
                print(f"   Deleting {epic_key}...")
                success = await jira_client.delete_issue(epic_key, delete_subtasks=False)
                if success:
                    print(f"   ✅ Deleted {epic_key}")
                else:
                    print(f"   ⚠️  Could not delete {epic_key}")
            except Exception as e:
                print(f"   ❌ Error deleting {epic_key}: {e}")
        print()
    
    # Generate new epic content using AI
    print("🤖 Generating new epic based on initiative and Notion context...")
    
    prompt = f"""You are creating a single Jira Epic that captures the essence of an initiative.

Initiative Summary: {initiative_summary}

Initiative Description:
{initiative_desc_text}

Context from Notion workspace (OKRs, projects, existing PRDs, strategic goals):
{notion_context.get('workspace_knowledge', '')[:4000] if notion_context.get('workspace_knowledge') else 'No additional context available'}

Create a comprehensive Epic that:
1. Captures the core objective and essence of this initiative
2. Is aligned with company OKRs and strategic goals from Notion
3. Includes clear deliverables and outcomes
4. Is actionable and well-structured
5. Uses proper terminology and references from the Notion workspace

Provide the epic in this format:

EPIC_SUMMARY: [A clear, concise epic summary/title]

EPIC_DESCRIPTION:
[Detailed description with:
- Overview and objectives
- Key deliverables
- Success criteria
- Dependencies or related work
- Alignment with OKRs/strategic goals]

The epic should be comprehensive but focused - it should capture everything important from the initiative in a single, well-structured epic.
"""
    
    try:
        response = await gemini_client.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1200
        )
        
        # Parse response
        epic_summary = initiative_summary  # Default
        epic_description = initiative_desc_text  # Default
        
        lines = response.split("\n")
        current_section = None
        description_parts = []
        
        for line in lines:
            if line.startswith("EPIC_SUMMARY:"):
                epic_summary = line.split(":", 1)[1].strip()
            elif line.startswith("EPIC_DESCRIPTION:"):
                current_section = "description"
            elif current_section == "description":
                description_parts.append(line)
        
        if description_parts:
            epic_description = "\n".join(description_parts).strip()
        
        # If parsing failed, use the full response
        if not epic_summary or epic_summary == initiative_summary:
            # Try to extract first line as summary
            first_line = response.split("\n")[0].strip()
            if first_line and len(first_line) < 200:
                epic_summary = first_line.replace("EPIC_SUMMARY:", "").strip()
            else:
                epic_summary = f"Epic: {initiative_summary}"
        
        if not epic_description or epic_description == initiative_desc_text:
            epic_description = response
        
        print(f"✅ Generated epic:")
        print(f"   Summary: {epic_summary}")
        print(f"   Description length: {len(epic_description)} chars\n")
        
    except Exception as e:
        print(f"❌ Error generating epic: {e}")
        # Use initiative as fallback
        epic_summary = f"Epic: {initiative_summary}"
        epic_description = initiative_desc_text
        print(f"   Using initiative content as fallback\n")
    
    # Create the new epic
    print("💾 Creating new epic in Jira...")
    try:
        # Convert description to ADF format (required for Jira API v3)
        adf_description = jira_client.text_to_adf(epic_description)
        
        # Required fields for Epic:
        # - customfield_10306: Overview (required) - needs ADF format
        # - customfield_11078: Planned or Unplanned (required multicheckbox) - use "Planned"
        # - parent: Link to initiative (required)
        additional_fields = {
            "parent": {"key": initiative_key},  # Link to initiative (required)
            "customfield_10306": adf_description,  # Overview (required) - ADF format
            "customfield_11078": [{"value": "Planned"}],  # Planned or Unplanned (required)
            "customfield_10374": [{"value": "Q1 26"}],  # Quarter
        }
        
        new_epic = await jira_client.create_issue(
            project_key=project_key,
            summary=epic_summary,
            description=adf_description,  # Description in ADF format
            issue_type="Epic",
            additional_fields=additional_fields
        )
        
        epic_key = new_epic.get('key')
        print(f"✅ Created new epic: {epic_key}")
        print(f"   Summary: {epic_summary}")
        print(f"   URL: {context.jira_url}/browse/{epic_key}")
        
        # Try to link epic to initiative (if possible)
        # This depends on how your Jira is configured
        print(f"\n💡 Note: You may need to manually link {epic_key} to initiative {initiative_key}")
        
        return epic_key
        
    except Exception as e:
        print(f"❌ Error creating epic: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 recreate_epic_for_initiative.py <INITIATIVE_KEY> [EPIC_KEY1] [EPIC_KEY2] ...")
        print("\nExample:")
        print("  python3 recreate_epic_for_initiative.py CSSV-1880 CSSV-1881 CSSV-1882")
        print("\nIf epic keys are not provided, the script will create a new epic without deleting old ones.")
        sys.exit(1)
    
    initiative_key = sys.argv[1]
    epic_keys_to_delete = sys.argv[2:] if len(sys.argv) > 2 else []
    
    asyncio.run(recreate_epic(initiative_key, epic_keys_to_delete))


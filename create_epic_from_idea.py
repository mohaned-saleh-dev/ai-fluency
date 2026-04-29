#!/usr/bin/env python3
"""
Create an epic based on idea bank content.
"""

import asyncio
import sys
import warnings
from pathlib import Path

# Suppress warnings
warnings.filterwarnings('ignore', category=FutureWarning)

sys.path.insert(0, str(Path(__file__).parent))

from prd_ticket_agent.config import load_context_from_env
from prd_ticket_agent.integrations.jira_client import JiraClient
from prd_ticket_agent.integrations.gemini_client import GeminiClient


async def create_epic_from_idea(initiative_key: str, idea_content: str):
    """Create epic based on idea bank content."""
    print(f"🚀 Creating Epic for Initiative: {initiative_key}\n")
    
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
    
    # Get initiative
    print(f"📋 Fetching initiative {initiative_key}...")
    try:
        initiative = await jira_client.get_issue(initiative_key)
        fields = initiative.get('fields', {})
        project_key = fields.get('project', {}).get('key', 'CSSV')
        print(f"✅ Found initiative: {fields.get('summary', 'N/A')}\n")
    except Exception as e:
        print(f"❌ Error fetching initiative: {e}")
        return
    
    # Generate epic content from idea bank
    print("🤖 Generating epic from idea bank content...")
    
    prompt = f"""Create a comprehensive Jira Epic based on this idea bank content:

{idea_content}

Requirements:
1. Create a clear, actionable epic summary (title)
2. Create a detailed epic description that includes:
   - Overview: What we're building and why
   - Problem Statement: The current issues
   - Solution: The specific approach (entry points, features)
   - Success Metrics: How we'll measure success
   - Key Deliverables: What needs to be built
   - Dependencies: Any related work

The epic should be:
- Specific and actionable
- Aligned with the idea bank content
- Professional and clear
- Include all key details from the idea bank

Format:
EPIC_SUMMARY: [Clear, concise title]

EPIC_DESCRIPTION:
[Comprehensive description with all sections]
"""
    
    try:
        response = await gemini_client.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        # Parse response
        epic_summary = ""
        epic_description = ""
        
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
        
        # Fallback if parsing failed
        if not epic_summary:
            epic_summary = "Enhance Help Center Visibility and Discoverability in Tamara App"
        if not epic_description:
            epic_description = idea_content
        
        print(f"✅ Generated epic:")
        print(f"   Summary: {epic_summary}")
        print(f"   Description: {len(epic_description)} chars\n")
        
    except Exception as e:
        print(f"❌ Error generating epic: {e}")
        # Use idea content directly
        epic_summary = "Enhance Help Center Visibility and Discoverability in Tamara App"
        epic_description = idea_content
        print(f"   Using idea content directly\n")
    
    # Convert to ADF
    adf_description = jira_client.text_to_adf(epic_description)
    
    # Create the epic
    print("💾 Creating epic in Jira...")
    try:
        additional_fields = {
            "parent": {"key": initiative_key},
            "customfield_10306": adf_description,  # Overview (required)
            "customfield_11078": [{"value": "Planned"}],  # Planned or Unplanned (required)
            "customfield_10374": [{"value": "Q1 26"}],  # Quarter
        }
        
        new_epic = await jira_client.create_issue(
            project_key=project_key,
            summary=epic_summary,
            description=adf_description,
            issue_type="Epic",
            additional_fields=additional_fields
        )
        
        epic_key = new_epic.get('key')
        print(f"✅ Created epic: {epic_key}")
        print(f"   Summary: {epic_summary}")
        print(f"   URL: {context.jira_url}/browse/{epic_key}")
        print(f"   Parent: {initiative_key}")
        print(f"   Quarter: Q1 26")
        
        return epic_key
        
    except Exception as e:
        print(f"❌ Error creating epic: {e}")
        return None


if __name__ == "__main__":
    idea_content = """## Section 1: What and Why?

**What is your idea?**

Enhance the **visibility and discoverability** of the Help Center within the **Tamara app**. Today, access points are limited and not prominently surfaced, meaning customers often overlook self-serve options and default to contacting support. This initiative aims to place Help Center entry points in **high-traffic areas of the app** and use contextual nudges to guide customers towards self-service.

**Why should we do it?**

- Current in-app Help Center visibility is **low**, resulting in underutilization of articles and self-serve flows.
- Customers **struggle to find the Help Center entry points**, driving higher contact rate for Phone Support
- By improving visibility, we can increase Help Center adoption, reduce inbound contacts, and improve **CES** through faster resolutions.
- Supports CareTech goals of **deflection, automation, and reduced cost-to-serve**.

---

## Section 2: Problem, Solution, and Hypothesis

**Problem or Opportunity:**

- Many customers don't know the Help Center exists within the app.
- The Help Center entry is hidden or secondary, leading to low awareness and traffic.
- Customers miss self-serve opportunities, escalating to live support prematurely.

**Solution:**

- Add **prominent Help Center entry points** across app journeys:
    - Home Screen
    - In-app menu/navigation.
    - Contextual CTAs (e.g., refund status page → "See related Help Center article").
    - Chat pre-handoff → show relevant articles before escalating.
    - Push banners for major incidents linking to Help Center updates.
- Experiment with **A/B placement** to maximize click-through.
- Ensure **AR/EN parity** and consistent Help Center branding.

**Hypothesis:**

If we improve Help Center visibility in the app, then **self-serve usage will increase**, **contact rates will decrease**, and customers will resolve issues faster, improving CES."""
    
    initiative_key = sys.argv[1] if len(sys.argv) > 1 else "CSSV-1880"
    
    asyncio.run(create_epic_from_idea(initiative_key, idea_content))













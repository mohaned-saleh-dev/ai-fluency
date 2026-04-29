#!/usr/bin/env python3
"""
Enrich Jira Epics with content and dates using Notion and Jira context.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from prd_ticket_agent import PRDTicketAgent
from prd_ticket_agent.config import load_context_from_env
from prd_ticket_agent.integrations.jira_client import JiraClient
from prd_ticket_agent.integrations.gemini_client import GeminiClient


async def get_epic_examples(jira_client: JiraClient, project_key: str = "CSSV") -> List[Dict[str, Any]]:
    """Get example epics from the project to understand patterns."""
    examples = []
    
    # Since search doesn't work, we'll need to work with what we can get
    # Try to get recent epics by fetching issues we know about
    # For now, return empty - we'll use Notion context instead
    return examples


async def estimate_epic_duration(
    epic_content: str,
    notion_context: Dict[str, Any],
    gemini_client: GeminiClient
) -> Dict[str, Any]:
    """
    Estimate duration for an epic based on content and similar work.
    
    Returns:
        Dict with 'start_date', 'end_date', 'duration_weeks'
    """
    # Build prompt for estimation
    prompt = f"""Based on the following epic description and context from similar work, estimate:
1. How many weeks this epic will take
2. A realistic start date (assuming Q1 2026 starts Jan 1, 2026)
3. An end date

Epic Description:
{epic_content}

Context from similar work:
{notion_context.get('workspace_knowledge', '')[:2000] if notion_context.get('workspace_knowledge') else 'No additional context'}

Provide your estimate in this format:
DURATION_WEEKS: [number]
START_DATE: YYYY-MM-DD
END_DATE: YYYY-MM-DD
REASONING: [brief explanation]
"""
    
    try:
        response = await gemini_client.generate_text(
            prompt=prompt,
            temperature=0.3,
            max_tokens=300
        )
        
        # Parse response
        duration_weeks = 4  # Default
        start_date = "2026-01-06"  # Default: First Monday of Q1 2026
        end_date = "2026-03-28"  # Default: End of Q1 2026
        
        lines = response.split("\n")
        for line in lines:
            if "DURATION_WEEKS:" in line:
                try:
                    duration_weeks = int(line.split(":")[1].strip())
                except:
                    pass
            elif "START_DATE:" in line:
                try:
                    start_date = line.split(":")[1].strip()
                except:
                    pass
            elif "END_DATE:" in line:
                try:
                    end_date = line.split(":")[1].strip()
                except:
                    pass
        
        # Calculate dates if not parsed
        if start_date == "2026-01-06":
            start = datetime(2026, 1, 6)  # First Monday
            end = start + timedelta(weeks=duration_weeks)
            end_date = end.strftime("%Y-%m-%d")
        
        return {
            "duration_weeks": duration_weeks,
            "start_date": start_date,
            "end_date": end_date,
            "reasoning": response
        }
    except Exception as e:
        print(f"  ⚠️  Estimation error: {e}")
        # Default estimates
        return {
            "duration_weeks": 4,
            "start_date": "2026-01-06",
            "end_date": "2026-02-03",
            "reasoning": "Default estimate"
        }


async def enrich_epic_content(
    epic: Dict[str, Any],
    notion_context: Dict[str, Any],
    gemini_client: GeminiClient
) -> str:
    """Enrich epic description using Notion context."""
    current_summary = epic.get('fields', {}).get('summary', '')
    current_description = epic.get('fields', {}).get('description', '')
    
    # Extract text from description
    desc_text = ""
    if current_description:
        if isinstance(current_description, dict):
            desc_text = gemini_client._extract_text_from_adf(current_description) if hasattr(gemini_client, '_extract_text_from_adf') else str(current_description)
        else:
            desc_text = str(current_description)
    
    epic_content = f"{current_summary}\n\n{desc_text}"
    
    prompt = f"""You are enriching a Jira Epic description. Use context from the Notion workspace to add:
- More detailed description
- Clear objectives and goals
- Key deliverables
- Dependencies or related work
- Success criteria

Current Epic:
{epic_content}

Context from Notion workspace (OKRs, projects, existing work):
{notion_context.get('workspace_knowledge', '')[:3000] if notion_context.get('workspace_knowledge') else 'No additional context available'}

Provide an enriched, detailed description for this epic. Keep it professional and actionable."""
    
    try:
        enriched = await gemini_client.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_tokens=800
        )
        return enriched
    except Exception as e:
        print(f"  ⚠️  Enrichment error: {e}")
        return desc_text or current_summary


async def enrich_initiative_epics(initiative_key: str = "CSSV-2044"):
    """Enrich all epics in an initiative."""
    print(f"🚀 Enriching Epics for Initiative: {initiative_key}\n")
    
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
        print(f"✅ Found: {fields.get('summary', 'N/A')}")
        print(f"   Type: {fields.get('issuetype', {}).get('name', 'N/A')}\n")
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
    
    # Try to find epics - check if epic keys are provided as command line args
    import sys
    epic_keys = []
    
    if len(sys.argv) > 2:
        # Epic keys provided as additional arguments
        epic_keys = [key.strip() for key in sys.argv[2:]]
        print(f"📋 Using epic keys from command line: {', '.join(epic_keys)}\n")
    else:
        # Try to find epics from initiative links or ask user
        print("🔍 Looking for epics...")
        
        # Check for issue links that might be epics
        issue_links = fields.get('issuelinks', [])
        subtasks = fields.get('subtasks', [])
        
        potential_epics = []
        for link in issue_links:
            outward = link.get('outwardIssue')
            inward = link.get('inwardIssue')
            if outward and outward.get('fields', {}).get('issuetype', {}).get('name') == 'Epic':
                potential_epics.append(outward.get('key'))
            if inward and inward.get('fields', {}).get('issuetype', {}).get('name') == 'Epic':
                potential_epics.append(inward.get('key'))
        
        if potential_epics:
            epic_keys = potential_epics
            print(f"✅ Found {len(epic_keys)} linked epics: {', '.join(epic_keys)}\n")
        else:
            # Ask user for epic keys
            print("⚠️  Note: Jira search API is not available.")
            print("   I couldn't find epics automatically.\n")
            epic_keys_input = input("Enter epic keys (comma-separated, e.g., CSSV-2045,CSSV-2046) or press Enter to skip: ").strip()
            
            if not epic_keys_input:
                print("\n💡 To enrich epics, provide them as:")
                print("   python3 enrich_epics.py CSSV-2044 CSSV-2045 CSSV-2046 CSSV-2047")
                print("   Or run this script and enter epic keys when prompted.\n")
                return
            
            epic_keys = [key.strip() for key in epic_keys_input.split(",")]
    
    print(f"\n🔧 Enriching {len(epic_keys)} epics...\n")
    
    for i, epic_key in enumerate(epic_keys, 1):
        print(f"{i}. Processing {epic_key}...")
        
        try:
            # Get epic
            epic = await jira_client.get_issue(epic_key)
            epic_fields = epic.get('fields', {})
            current_summary = epic_fields.get('summary', '')
            
            print(f"   Current: {current_summary}")
            
            # Enrich content
            print("   📝 Enriching description...")
            enriched_description = await enrich_epic_content(epic, notion_context, gemini_client)
            
            # Estimate duration
            print("   📅 Estimating duration...")
            epic_content = f"{current_summary}\n\n{enriched_description[:500]}"
            dates = await estimate_epic_duration(epic_content, notion_context, gemini_client)
            
            # Prepare update
            update_fields = {}
            
            # Update description
            # Note: Jira description format might need ADF - for now use plain text
            update_fields["description"] = enriched_description
            
            # Update quarter field - based on exploration, try common patterns
            # Quarter is likely a select list field
            quarter_value = "Q1 26"
            # Try to find quarter field - common patterns:
            # - customfield_10374 (list field)
            # - customfield_10967 (list field)
            # We'll try updating with the value structure
            quarter_field_candidates = ["customfield_10374", "customfield_10967"]
            
            # Update dates - found from exploration:
            # customfield_10333: start date (string format "YYYY-MM-DD")
            # customfield_10356: end date (string format "YYYY-MM-DD")
            try:
                start_date_obj = datetime.strptime(dates['start_date'], "%Y-%m-%d")
                end_date_obj = datetime.strptime(dates['end_date'], "%Y-%m-%d")
                
                # Jira date format: "2026-01-06"
                update_fields["customfield_10333"] = dates['start_date']  # Start date
                update_fields["customfield_10356"] = dates['end_date']    # End date
            except Exception as e:
                print(f"      ⚠️  Date parsing error: {e}")
            
            # Quarter field format: customfield_10374 with structure [{"value": "Q1 26"}]
            # Can also use [{"value": "Q1 26", "id": "11674"}] but value alone should work
            quarter_field_update = {"customfield_10374": [{"value": quarter_value}]}
            
            print(f"   ✅ Estimated: {dates['duration_weeks']} weeks")
            print(f"      Start: {dates['start_date']}")
            print(f"      End: {dates['end_date']}")
            
            # Update the epic
            print("   💾 Updating epic in Jira...")
            try:
                # First update description
                await jira_client.update_issue(epic_key, {"description": enriched_description})
                print(f"   ✅ Updated description")
                
                # Try to update dates
                date_fields = {}
                if "customfield_10333" in update_fields:
                    date_fields["customfield_10333"] = update_fields["customfield_10333"]
                if "customfield_10356" in update_fields:
                    date_fields["customfield_10356"] = update_fields["customfield_10356"]
                
                if date_fields:
                    try:
                        await jira_client.update_issue(epic_key, date_fields)
                        print(f"   ✅ Updated dates")
                    except Exception as e:
                        print(f"   ⚠️  Date update error: {e}")
                
                # Update quarter field
                try:
                    await jira_client.update_issue(epic_key, quarter_field_update)
                    print(f"   ✅ Updated quarter to Q1 26")
                except Exception as e:
                    print(f"   ⚠️  Quarter update error: {e}")
                    print(f"      Please set Quarter to 'Q1 26' manually")
                
                print(f"   ✅ Successfully updated {epic_key}")
                
            except Exception as e:
                print(f"   ❌ Update error: {e}")
                print(f"   📋 Here's what to update manually:")
                print(f"      Description: {enriched_description[:200]}...")
                print(f"      Quarter: Q1 26")
                print(f"      Start Date: {dates['start_date']}")
                print(f"      End Date: {dates['end_date']}")
            
        except Exception as e:
            print(f"   ❌ Error processing {epic_key}: {e}")
        
        print()
    
    print("✅ Done!")


if __name__ == "__main__":
    import sys
    initiative_key = sys.argv[1] if len(sys.argv) > 1 else "CSSV-2044"
    asyncio.run(enrich_initiative_epics(initiative_key))


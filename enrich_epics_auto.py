#!/usr/bin/env python3
"""
Automatically enrich Jira Epics with content and dates using Notion and Jira context.
This version works with epic keys provided as arguments.
"""

import asyncio
import sys
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Suppress warnings
warnings.filterwarnings('ignore', category=FutureWarning)

sys.path.insert(0, str(Path(__file__).parent))

from prd_ticket_agent import PRDTicketAgent
from prd_ticket_agent.config import load_context_from_env
from prd_ticket_agent.integrations.jira_client import JiraClient
from prd_ticket_agent.integrations.gemini_client import GeminiClient


async def estimate_epic_duration(
    epic_content: str,
    notion_context: Dict[str, Any],
    gemini_client: GeminiClient,
    similar_epics: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Estimate duration for an epic based on content and similar work.
    
    Returns:
        Dict with 'start_date', 'end_date', 'duration_weeks'
    """
    # Build context from similar epics
    similar_context = ""
    if similar_epics:
        similar_context = "\n\nSimilar epics for reference:\n"
        for epic in similar_epics[:3]:
            summary = epic.get('fields', {}).get('summary', 'N/A')
            similar_context += f"- {summary}\n"
    
    # Build prompt for estimation
    prompt = f"""You are estimating the duration for a Jira Epic. Based on the epic description and context from similar work, provide realistic estimates.

Epic Description:
{epic_content}

Context from Notion workspace (OKRs, projects, existing work):
{notion_context.get('workspace_knowledge', '')[:2000] if notion_context.get('workspace_knowledge') else 'No additional context'}{similar_context}

Q1 2026 runs from January 1, 2026 to March 31, 2026 (13 weeks).

Consider:
- Typical epic duration is 4-8 weeks
- Account for dependencies and complexity
- Start dates should be realistic (account for planning, dependencies)
- End dates should be within Q1 2026

Provide your estimate in this exact format:
DURATION_WEEKS: [number]
START_DATE: YYYY-MM-DD
END_DATE: YYYY-MM-DD
REASONING: [brief 1-2 sentence explanation]
"""
    
    try:
        response = await gemini_client.generate_text(
            prompt=prompt,
            temperature=0.3,
            max_tokens=300
        )
        
        # Parse response
        duration_weeks = 6  # Default
        start_date = "2026-01-06"  # Default: First Monday of Q1 2026
        end_date = "2026-02-17"  # Default: Mid-Q1
        
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
        
        # Validate dates are in Q1 2026
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            q1_start = datetime(2026, 1, 1)
            q1_end = datetime(2026, 3, 31)
            
            if start < q1_start:
                start_date = "2026-01-06"  # First Monday
                start = datetime(2026, 1, 6)
            
            if end > q1_end:
                end_date = "2026-03-28"  # Last Friday
                end = datetime(2026, 3, 28)
            
            # Recalculate duration if needed
            if start and end:
                duration_weeks = max(1, (end - start).days // 7)
                
        except:
            # If parsing fails, use defaults
            start = datetime(2026, 1, 6)
            end = start + timedelta(weeks=duration_weeks)
            if end > datetime(2026, 3, 31):
                end = datetime(2026, 3, 28)
            start_date = start.strftime("%Y-%m-%d")
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
        start = datetime(2026, 1, 6)
        end = start + timedelta(weeks=6)
        if end > datetime(2026, 3, 31):
            end = datetime(2026, 3, 28)
        return {
            "duration_weeks": 6,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "reasoning": "Default estimate based on typical epic duration"
        }


async def enrich_epic_content(
    epic: Dict[str, Any],
    notion_context: Dict[str, Any],
    gemini_client: GeminiClient,
    initiative_summary: str = ""
) -> str:
    """Enrich epic description using Notion context."""
    current_summary = epic.get('fields', {}).get('summary', '')
    current_description = epic.get('fields', {}).get('description', '')
    
    # Extract text from description
    desc_text = ""
    if current_description:
        if isinstance(current_description, dict):
            # Try to extract from ADF format
            try:
                content = current_description.get('content', [])
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        para = item.get('content', [])
                        for p in para:
                            if isinstance(p, dict) and p.get('type') == 'text':
                                text_parts.append(p.get('text', ''))
                desc_text = ' '.join(text_parts)
            except:
                desc_text = str(current_description)
        else:
            desc_text = str(current_description)
    
    epic_content = f"Summary: {current_summary}\n\nDescription: {desc_text}"
    
    prompt = f"""You are enriching a Jira Epic description. Use context from the Notion workspace to add:
- More detailed and comprehensive description
- Clear objectives and goals aligned with company OKRs
- Key deliverables and milestones
- Dependencies or related work
- Success criteria and metrics
- Technical considerations if relevant

Current Epic:
{epic_content}

Parent Initiative: {initiative_summary}

Context from Notion workspace (OKRs, projects, existing PRDs, strategic goals):
{notion_context.get('workspace_knowledge', '')[:4000] if notion_context.get('workspace_knowledge') else 'No additional context available'}

Provide an enriched, detailed, professional description for this epic. Make it actionable and aligned with company goals. Use markdown formatting for structure."""
    
    try:
        enriched = await gemini_client.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1000
        )
        return enriched
    except Exception as e:
        print(f"  ⚠️  Enrichment error: {e}")
        return desc_text or current_summary


async def enrich_epics(initiative_key: str, epic_keys: List[str]):
    """Enrich epics with content, dates, and quarter."""
    print(f"🚀 Enriching Epics for Initiative: {initiative_key}\n")
    print(f"📋 Processing {len(epic_keys)} epics: {', '.join(epic_keys)}\n")
    
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
        print(f"✅ Found: {initiative_summary}\n")
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
    
    # Fetch all epics first to get context
    print("📥 Fetching epic details...")
    epics = []
    for epic_key in epic_keys:
        try:
            epic = await jira_client.get_issue(epic_key)
            epics.append(epic)
            summary = epic.get('fields', {}).get('summary', 'N/A')
            print(f"  ✅ {epic_key}: {summary}")
        except Exception as e:
            print(f"  ❌ Error fetching {epic_key}: {e}")
    
    if not epics:
        print("❌ No epics to process")
        return
    
    print(f"\n🔧 Enriching {len(epics)} epics...\n")
    
    # Process each epic
    results = []
    for i, epic in enumerate(epics, 1):
        epic_key = epic.get('key')
        epic_fields = epic.get('fields', {})
        current_summary = epic_fields.get('summary', '')
        
        print(f"{i}. Processing {epic_key}...")
        print(f"   Current: {current_summary}")
        
        try:
            # Enrich content
            print("   📝 Enriching description...")
            enriched_description = await enrich_epic_content(
                epic, 
                notion_context, 
                gemini_client,
                initiative_summary
            )
            
            # Estimate duration
            print("   📅 Estimating duration...")
            epic_content = f"{current_summary}\n\n{enriched_description[:500]}"
            dates = await estimate_epic_duration(epic_content, notion_context, gemini_client, epics)
            
            print(f"   ✅ Estimated: {dates['duration_weeks']} weeks")
            print(f"      Start: {dates['start_date']}")
            print(f"      End: {dates['end_date']}")
            
            # Prepare updates
            update_fields = {}
            
            # Update description (plain text for now - Jira will handle formatting)
            update_fields["description"] = enriched_description
            
            # Update dates
            update_fields["customfield_10333"] = dates['start_date']  # Start date
            update_fields["customfield_10356"] = dates['end_date']    # End date
            
            # Update quarter to Q1 26
            update_fields["customfield_10374"] = [{"value": "Q1 26"}]
            
            # Update the epic
            print("   💾 Updating epic in Jira...")
            try:
                await jira_client.update_issue(epic_key, update_fields)
                print(f"   ✅ Successfully updated {epic_key}")
                results.append({
                    "epic": epic_key,
                    "status": "success",
                    "dates": dates,
                    "description_length": len(enriched_description)
                })
            except Exception as e:
                print(f"   ❌ Update error: {e}")
                print(f"   📋 Manual update needed for {epic_key}:")
                print(f"      Quarter: Q1 26")
                print(f"      Start Date: {dates['start_date']}")
                print(f"      End Date: {dates['end_date']}")
                print(f"      Description: {enriched_description[:200]}...")
                results.append({
                    "epic": epic_key,
                    "status": "error",
                    "error": str(e),
                    "dates": dates
                })
            
        except Exception as e:
            print(f"   ❌ Error processing {epic_key}: {e}")
            results.append({
                "epic": epic_key,
                "status": "error",
                "error": str(e)
            })
        
        print()
    
    # Summary
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    successful = sum(1 for r in results if r.get('status') == 'success')
    print(f"✅ Successfully updated: {successful}/{len(results)}")
    print(f"❌ Errors: {len(results) - successful}/{len(results)}")
    print()
    
    for result in results:
        status_icon = "✅" if result.get('status') == 'success' else "❌"
        print(f"{status_icon} {result['epic']}")
        if result.get('dates'):
            print(f"   Dates: {result['dates']['start_date']} to {result['dates']['end_date']} ({result['dates']['duration_weeks']} weeks)")
        if result.get('error'):
            print(f"   Error: {result['error']}")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 enrich_epics_auto.py <INITIATIVE_KEY> <EPIC_KEY1> [EPIC_KEY2] ...")
        print("\nExample:")
        print("  python3 enrich_epics_auto.py CSSV-2044 CSSV-2045 CSSV-2046 CSSV-2047")
        print("\nTo find epic keys:")
        print("  1. Go to your Jira board")
        print("  2. Filter by the initiative")
        print("  3. Copy the epic keys (e.g., CSSV-2045, CSSV-2046)")
        sys.exit(1)
    
    initiative_key = sys.argv[1]
    epic_keys = sys.argv[2:]
    
    asyncio.run(enrich_epics(initiative_key, epic_keys))













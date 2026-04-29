#!/usr/bin/env python3
"""
Create UFME epic based on idea bank and PRD content.
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


async def create_ufme_epic(initiative_key: str, idea_content: str, prd_content: str):
    """Create epic based on idea bank and PRD content."""
    print(f"🚀 Creating UFME Epic for Initiative: {initiative_key}\n")
    
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
    
    # Generate epic content from idea bank and PRD
    print("🤖 Generating epic from idea bank and PRD...")
    
    prompt = f"""Create a comprehensive Jira Epic for Unified Feedback Management Enablement (UFME) based on this content:

IDEA BANK:
{idea_content}

PRD SUMMARY:
{prd_content[:3000]}

This is about building a centralized survey data infrastructure that:
- Unifies all customer satisfaction survey responses across every support channel (in-app, chat, phone, SMS, email)
- Creates a single, normalized source of truth for survey data
- Enables consistent, comparable analysis of customer satisfaction
- Powers unified dashboarding and future multi-channel survey delivery logic
- Includes retry mechanisms, suppression, and lifecycle management

Key components:
1. Primary Survey Data Store (centralized warehouse)
2. Multi-source ingestion (in-app, chat, phone, email, SMS)
3. ETL pipelines for data sync
4. Retry engine for multi-channel fallback
5. Suppression engine to prevent duplicates
6. Unified Tableau dashboards

This is a DATA AND PLATFORM ENABLER - infrastructure and backend, not UI.

Create:
1. A clear, actionable epic summary (title) that captures the essence
2. A detailed epic description that includes:
   - Overview: What we're building (centralized survey data infrastructure)
   - Problem: Why we need it (fragmented feedback, no unified view, can't compare across channels)
   - Solution: Core infrastructure components (data store, ingestion, ETL, retry, suppression)
   - Key Deliverables: What needs to be built
   - Success Metrics: Issue Resolution Rate ≥85%, Survey Response Rate ≥50%, Attribution ≥95%
   - Technical Approach: Data flows, schema, ETL jobs

The epic should be:
- Specific and technical (this is infrastructure work)
- Aligned with the PRD scope
- Professional and clear
- Focused on Phase 1 foundation work

Format:
EPIC_SUMMARY: [Clear, concise title]

EPIC_DESCRIPTION:
[Comprehensive description with all sections]
"""
    
    try:
        response = await gemini_client.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_tokens=2000
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
            epic_summary = "Build Centralized Survey Data Infrastructure for Unified Feedback Management"
        if not epic_description:
            # Create a comprehensive description from the content
            epic_description = f"""{idea_content}

---

## PRD Overview

{prd_content[:2000]}

## Key Components

1. **Primary Survey Data Store** - Singular source of truth in analytics DB
2. **Multi-Source Ingestion** - In-app (Mobile SDK), Chat (ETL), Phone/IVR, Email, SMS
3. **ETL Pipelines** - Daily sync jobs (Airflow/DBT) from Chat Service DB, Self-Serve DB, Voice Gateway
4. **Retry Engine** - Multi-channel fallback for expired surveys
5. **Suppression Engine** - Prevent duplicate surveys within 24h
6. **Unified Tableau Dashboards** - Cross-channel reporting and analysis

## Success Metrics (Phase 1)

- Issue Resolution Rate ≥ 85%
- Survey Response Rate ≥ 50%
- Attribution Rate ≥ 95%
- Duplicate Survey Rate < 2%
- Re-ask after skip = 0%

## Technical Architecture

- Central Warehouse schema with normalized survey data
- Real-time POST from Mobile SDK for in-app surveys
- Daily ETL sync from Chat Service DB
- Batch ingestion from IVR/Voice Gateway
- Rudderstack integration for event tracking
- Data retention: 3 years"""
        
        print(f"✅ Generated epic:")
        print(f"   Summary: {epic_summary}")
        print(f"   Description: {len(epic_description)} chars\n")
        
    except Exception as e:
        print(f"❌ Error generating epic: {e}")
        # Use content directly
        epic_summary = "Build Centralized Survey Data Infrastructure for Unified Feedback Management"
        epic_description = f"{idea_content}\n\n---\n\n{prd_content[:3000]}"
        print(f"   Using content directly\n")
    
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

### **What is your idea?**

Build a **Centralized Survey Data Infrastructure** to unify all customer satisfaction survey responses across **every support channel** (in-app, chat, phone, SMS, email) into a **single, normalized source of truth**.

This initiative focuses on creating the foundational data layer that:

- Consolidates survey responses regardless of where or how the survey was delivered
- Standardizes survey data models across channels
- Enables consistent, comparable analysis of customer satisfaction
- Powers unified dashboarding and future multi-channel survey delivery logic

This is a **data and platform enabler**, not a UI or survey-creation initiative.

---

### **Why should we do it?**

Today, customer satisfaction data is fragmented by channel and tooling, making it difficult to:

- Compare CSAT/CES/NPS across chat, phone, in-app, and email
- Understand the true impact of automation vs live support
- Attribute satisfaction to specific interactions or journeys

A centralized survey data layer:

- Enables **holistic CX measurement**
- Improves decision-making by removing channel bias
- Creates a foundation for smarter survey delivery (retry, fallback, targeting)
- Reduces manual reporting effort and data inconsistencies

**Target audience:**

CX, Care, Product, Data, and Leadership teams relying on customer satisfaction metrics for performance tracking and prioritization.

---

## Section 2: Problem, Solution, and Hypothesis

### **Problem or Opportunity:**

Customer satisfaction surveys are currently:

- Collected across multiple systems and channels
- Stored in inconsistent formats
- Difficult to join back to the original customer interaction

As a result:

- Satisfaction metrics are siloed by channel
- Cross-channel comparisons are unreliable
- Reporting requires manual stitching and assumptions
- Survey data cannot easily support retry or fallback strategies

---

### **Relevant Data:**

- Surveys are triggered across multiple touchpoints (chat, IVR, in-app, email)
- Each channel has its own storage, schema, and limitations
- Survey results are a primary input into CX KPIs, but lack a unified view
- Existing dashboards require manual reconciliation across sources

---

### **Solution:**

Create a **centralized survey data infrastructure** that:

- Acts as the **single source of truth** for all survey submissions
- Ingests survey data from all channels (synchronous and asynchronous)
- Normalizes survey responses using a shared data model
- Links each survey to a specific interaction via a common interaction identifier
- Supports retry and fallback logic across channels
- Feeds unified dashboards for consistent analysis and reporting

This infrastructure will separate **survey delivery** from **survey analysis**, allowing each to evolve independently.

---

### **Hypothesis:**

If all customer satisfaction survey data is centralized and normalized across channels, we will gain a more accurate, comparable view of customer experience, reduce reporting inconsistencies, and enable better CX decisions by understanding satisfaction holistically rather than in channel-specific silos."""
    
    # PRD content (abbreviated for prompt, full content in script)
    prd_summary = """Unified Feedback Management Enablement (UFME) - Centralized survey data infrastructure that unifies all feedback signals (CSAT, ASAT, CES, Issue Resolution, NPS) across all support channels. Core components: Primary Survey Data Store, multi-source ingestion (in-app, chat, phone, email, SMS), ETL pipelines, retry engine, suppression engine, unified Tableau dashboards. Phase 1 success metrics: Issue Resolution Rate ≥85%, Survey Response Rate ≥50%, Attribution ≥95%."""
    
    initiative_key = sys.argv[1] if len(sys.argv) > 1 else "CSSV-1847"
    
    asyncio.run(create_ufme_epic(initiative_key, idea_content, prd_summary))













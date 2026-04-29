#!/usr/bin/env python3
"""
Create multiple UFME epics based on comprehensive breakdown:
- Backend/Infrastructure
- Channel Integrations
- Frontend/Reporting
"""

import asyncio
import sys
import warnings
from pathlib import Path
from typing import List, Dict

# Suppress warnings
warnings.filterwarnings('ignore', category=FutureWarning)

sys.path.insert(0, str(Path(__file__).parent))

from prd_ticket_agent.config import load_context_from_env
from prd_ticket_agent.integrations.jira_client import JiraClient
from prd_ticket_agent.integrations.gemini_client import GeminiClient


EPICS_BREAKDOWN = [
    {
        "summary": "UFME: Central Survey Data Store & Schema Design",
        "description": """## Overview
Build the foundational data infrastructure - the Central Survey Data Store with normalized schema that serves as the single source of truth for all survey submissions across all channels.

## Problem
Today survey data is fragmented across multiple systems (Chat DB, Self-Serve DB, Voice Gateway) with inconsistent schemas, making unified analysis impossible.

## Solution
Create a centralized warehouse table with standardized schema that:
- Stores all survey responses regardless of source channel
- Normalizes data models across channels (in-app, chat, phone, email, SMS)
- Links surveys to interactions via interaction_id
- Supports survey lifecycle states (in_progress, completed, skipped, expired, retried)

## Key Deliverables
- Central Warehouse schema design and implementation
- Normalized data model (survey_id, customer_id, interaction_id, survey_type, response_value, etc.)
- Data retention policy (3 years)
- Indexing strategy for customer-level and experience-level queries

## Success Metrics
- Schema supports all channel types
- Data attribution accuracy ≥ 99.9%
- Query performance < 500ms p99

## Technical Approach
- Design schema in Central Warehouse (OCI/GCP)
- Define field mappings for normalization
- Implement data quality constraints
- Set up partitioning strategy for performance""",
        "priority": "P0"
    },
    {
        "summary": "UFME: ETL Pipelines for Multi-Channel Survey Ingestion",
        "description": """## Overview
Build ETL pipelines (Airflow/DBT) to sync survey data from all source systems into the Central Survey Data Store.

## Problem
Survey data exists in siloed systems (Chat Service DB, Self-Serve DB, Voice Gateway) and needs to be consolidated into a unified store.

## Solution
Create daily ETL jobs that:
- Sync chat surveys from Chat Service DB
- Sync self-serve surveys from Self-Serve DB
- Ingest IVR/phone surveys from Voice Gateway
- Transform and normalize data using survey_field_map.yaml
- Handle data quality checks and error flagging

## Key Deliverables
- Chat Survey Sync ETL (daily)
- Self-Serve Survey Sync ETL (daily)
- IVR Response Sync ETL (daily)
- Data Quality Check ETL (daily)
- Error handling and alerting

## Success Metrics
- ETL job completion < 2 hours
- Data freshness in warehouse < 4 hours
- Zero data loss during sync
- Data quality error rate < 1%

## Technical Approach
- Airflow DAGs for orchestration
- DBT transformations for normalization
- survey_field_map.yaml for field mapping
- Retry logic for failed jobs
- Monitoring and alerting for pipeline health""",
        "priority": "P0"
    },
    {
        "summary": "UFME: Survey Retry & Suppression Engine",
        "description": """## Overview
Build the retry engine for multi-channel fallback and suppression engine to prevent duplicate surveys.

## Problem
Missed or expired surveys are lost, and customers can receive multiple surveys for the same interaction, leading to poor experience and data quality issues.

## Solution
Create engines that:
- Retry expired surveys (TTL = 1 hour) on fallback channels
- Suppress duplicate surveys within 24h window
- Enforce "one successful submission per interaction_id" rule
- Support channel priority for retry (in-app → push → email → SMS → IVR)

## Key Deliverables
- Retry Engine service
- Suppression Engine service
- Channel priority configuration
- Retry eligibility rules
- Suppression rules (skip, completed, 24h window)

## Success Metrics
- Retry Success Rate ≥ 15% (Phase 2)
- Duplicate Survey Rate < 2%
- Re-ask after skip = 0%
- Suppression accuracy = 100%

## Technical Approach
- UFME Core Service for eligibility checks
- State machine for survey lifecycle (in_progress → expired → retried)
- Channel fallback logic
- Suppression lookup service
- Integration with push notification service""",
        "priority": "P1"
    },
    {
        "summary": "UFME: In-App Survey Integration (Mobile SDK)",
        "description": """## Overview
Integrate in-app survey submission via Mobile SDK with real-time POST to Survey API.

## Problem
In-app surveys are currently stored in Self-Serve DB without unified schema or real-time availability for analysis.

## Solution
- Update Mobile SDK to POST survey responses to Survey API endpoint
- Real-time ingestion into Central Survey Data Store
- Support for CSAT, CES, Issue Resolution survey types
- Handle survey state (in_progress, completed, skipped)

## Key Deliverables
- Mobile SDK integration with Survey API
- Real-time POST endpoint for survey submission
- Survey state management in SDK
- Error handling and retry logic
- AR/EN localization support

## Success Metrics
- Survey submission latency < 500ms p99
- Submission success rate ≥ 99%
- Zero data loss
- Support for all in-app survey types

## Technical Approach
- Survey API endpoint (POST /surveys)
- Mobile SDK update for survey submission
- Authentication via customer_id
- ADF format for response_text
- Integration with Central Survey Data Store""",
        "priority": "P0"
    },
    {
        "summary": "UFME: Chat Survey Integration & ETL",
        "description": """## Overview
Integrate chat surveys by syncing from Chat Service DB to Central Survey Data Store via ETL.

## Problem
Chat surveys (CSAT, ASAT, Issue Resolution) are stored in Chat Service DB with different schema, making cross-channel comparison impossible.

## Solution
- Create ETL pipeline to sync chat surveys daily
- Normalize chat survey schema to unified format
- Map chat-specific fields (emoji_response) to standard response_value
- Link surveys to chat interactions via interaction_id

## Key Deliverables
- Chat Survey ETL pipeline (daily sync)
- Field mapping for chat schema (emoji → numeric)
- Chat interaction_id linking
- Data quality validation
- Error handling for sync failures

## Success Metrics
- Daily sync completion < 2 hours
- Data freshness < 4 hours
- Attribution rate ≥ 95%
- Zero data loss during sync

## Technical Approach
- Direct read from Chat Service DB
- DBT transformation for normalization
- survey_field_map.yaml for chat-specific mappings
- Airflow DAG for daily execution
- Monitoring and alerting""",
        "priority": "P0"
    },
    {
        "summary": "UFME: Phone/IVR Survey Integration",
        "description": """## Overview
Integrate phone/IVR survey responses by ingesting from Voice Gateway into Central Survey Data Store.

## Problem
IVR surveys are stored in voice system with batch-only access, preventing real-time analysis and cross-channel comparison.

## Solution
- Create batch ingestion pipeline from Voice Gateway
- Normalize IVR survey format (DTMF input) to standard schema
- Link surveys to phone interactions via interaction_id
- Support retry fallback from IVR to in-app/push

## Key Deliverables
- IVR Survey ETL pipeline (daily batch)
- Voice Gateway integration
- DTMF to response_value transformation
- Phone interaction_id linking
- Retry fallback support

## Success Metrics
- Batch ingestion completion < 2 hours
- Data freshness < 4 hours
- Attribution rate ≥ 95%
- Retry success rate ≥ 15%

## Technical Approach
- Batch export from Voice Gateway
- ETL transformation for DTMF normalization
- survey_field_map.yaml for IVR mappings
- Airflow DAG for daily execution
- Integration with retry engine""",
        "priority": "P1"
    },
    {
        "summary": "UFME: Email & SMS Survey Integration",
        "description": """## Overview
Integrate email and SMS survey responses into Central Survey Data Store.

## Problem
Email and SMS surveys are currently handled by channel tooling without unified storage or analysis capabilities.

## Solution
- Create ingestion pipelines for email and SMS surveys
- Normalize email/SMS response formats
- Link surveys to original interactions
- Support asynchronous survey delivery and response collection

## Key Deliverables
- Email survey ingestion pipeline
- SMS survey ingestion pipeline
- Response normalization for email/SMS formats
- Interaction linking
- Webhook/API integration points

## Success Metrics
- Ingestion latency < 4 hours
- Attribution rate ≥ 95%
- Response rate ≥ 50%
- Zero data loss

## Technical Approach
- Webhook endpoints for email/SMS responses
- ETL pipelines for batch processing
- Field mapping configuration
- Integration with retry engine for fallback""",
        "priority": "P1"
    },
    {
        "summary": "UFME: Unified Tableau Dashboards & Reporting",
        "description": """## Overview
Build unified Tableau dashboards that provide 360° customer feedback view across all channels with consistent, comparable metrics.

## Problem
Today leadership views multiple dashboards that cannot be reconciled, making it impossible to answer strategic questions about CX and channel performance.

## Solution
Create Tableau dashboards that:
- Aggregate CSAT, ASAT, CES, Issue Resolution, NPS across all channels
- Provide customer-level, experience-level, and channel-level views
- Enable cross-channel comparison
- Support filtering by customer, experience, channel, time period
- Show retry success rates and survey lifecycle metrics

## Key Deliverables
- Customer-Level Feedback Dashboard
- Experience-Level Analysis Dashboard
- Channel Comparison Dashboard
- Survey Lifecycle Dashboard
- Executive Summary Dashboard

## Success Metrics
- Dashboard load time < 5 seconds
- Data freshness < 4 hours
- Supports all required filters and breakdowns
- Zero reconciliation needed across dashboards

## Technical Approach
- Tableau data source from Central Survey Data Store
- Dashboard design following feedback analysis hierarchy
- Scheduled refreshes (4-hour cadence)
- User access controls
- Performance optimization for large datasets""",
        "priority": "P0"
    },
    {
        "summary": "UFME: Data Quality & Monitoring Infrastructure",
        "description": """## Overview
Build data quality checks, monitoring, and alerting infrastructure to ensure survey data accuracy and pipeline health.

## Problem
Without data quality guardrails, invalid data, duplicates, and pipeline failures can corrupt analysis and decision-making.

## Solution
Implement:
- Data quality validation rules (5-second rule, duplicate bounce, conflict flagging)
- Pipeline health monitoring and alerting
- Data quality dashboard
- Error status tracking (status = error for invalid data)
- Audit trail for survey submissions

## Key Deliverables
- Data quality validation rules
- ETL job monitoring and alerting
- Data quality dashboard
- Error tracking and reporting
- Audit logging

## Success Metrics
- Data quality error detection rate = 100%
- Pipeline failure alerting < 5 minutes
- Invalid data rate < 1%
- Zero undetected duplicates

## Technical Approach
- Validation rules in ETL pipelines
- Airflow monitoring and alerting
- Data quality checks in Central Warehouse
- Error status field in schema
- Logging and audit trail""",
        "priority": "P0"
    }
]


async def create_ufme_epics(initiative_key: str):
    """Create multiple UFME epics based on comprehensive breakdown."""
    print(f"🚀 Creating UFME Epics for Initiative: {initiative_key}\n")
    print(f"📋 Will create {len(EPICS_BREAKDOWN)} epics\n")
    
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
    
    # Create epics
    created_epics = []
    
    for i, epic_data in enumerate(EPICS_BREAKDOWN, 1):
        print(f"{i}. Creating: {epic_data['summary']}")
        
        # Convert description to ADF
        adf_description = jira_client.text_to_adf(epic_data['description'])
        
        try:
            additional_fields = {
                "parent": {"key": initiative_key},
                "customfield_10306": adf_description,  # Overview (required)
                "customfield_11078": [{"value": "Planned"}],  # Planned or Unplanned (required)
                "customfield_10374": [{"value": "Q1 26"}],  # Quarter
            }
            
            new_epic = await jira_client.create_issue(
                project_key=project_key,
                summary=epic_data['summary'],
                description=adf_description,
                issue_type="Epic",
                additional_fields=additional_fields
            )
            
            epic_key = new_epic.get('key')
            created_epics.append({
                "key": epic_key,
                "summary": epic_data['summary'],
                "priority": epic_data['priority']
            })
            
            print(f"   ✅ Created: {epic_key}")
            print(f"      Priority: {epic_data['priority']}\n")
            
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
    
    # Summary
    print("=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"✅ Successfully created {len(created_epics)} epics:\n")
    
    for epic in created_epics:
        print(f"  {epic['priority']} - {epic['key']}: {epic['summary']}")
        print(f"     URL: {context.jira_url}/browse/{epic['key']}\n")
    
    print("✅ Done!")


if __name__ == "__main__":
    initiative_key = sys.argv[1] if len(sys.argv) > 1 else "CSSV-1847"
    asyncio.run(create_ufme_epics(initiative_key))













# Enrich Jira Epics Guide

## Overview

The PRD Agent can enrich Jira epics with:
- ✅ **Enhanced descriptions** using Notion workspace context (OKRs, projects, existing PRDs)
- ✅ **Quarter assignment** (Q1 26)
- ✅ **Estimated start and end dates** based on work complexity and similar epics
- ✅ **Aligned content** with company goals and existing work patterns

## Quick Start

### Step 1: Get Epic Keys

Since Jira search API is not available, you need to provide epic keys manually:

1. Go to your Jira board: https://tamarapay.atlassian.net/jira/software/c/projects/CSSV/issues
2. Filter by initiative `CSSV-2044` or use the Q1 26 filter
3. Find all epics under the initiative
4. Copy the epic keys (e.g., `CSSV-2045`, `CSSV-2046`, `CSSV-2047`)

### Step 2: Run the Enrichment Script

```bash
cd /Users/mohaned.saleh/prd-ticket-agent
python3 enrich_epics_auto.py CSSV-2044 CSSV-2045 CSSV-2046 CSSV-2047
```

Replace the epic keys with your actual epic keys.

## What It Does

For each epic, the script will:

1. **Fetch the epic** from Jira
2. **Gather Notion context** from your workspace (OKRs, projects, existing PRDs)
3. **Enrich the description** using AI with:
   - Detailed objectives aligned with company goals
   - Key deliverables and milestones
   - Dependencies and related work
   - Success criteria
4. **Estimate duration** based on:
   - Epic complexity
   - Similar epics in your board
   - Notion context about project scope
5. **Set dates** within Q1 2026:
   - Start date (realistic, accounting for dependencies)
   - End date (within Q1 2026)
6. **Update Jira** with:
   - Enriched description
   - Quarter: Q1 26
   - Start date
   - End date

## Example Output

```
🚀 Enriching Epics for Initiative: CSSV-2044

📋 Processing 3 epics: CSSV-2045, CSSV-2046, CSSV-2047

📋 Fetching initiative CSSV-2044...
✅ Found: Partner Onboarding AI Chatbot (Phase 1) [P0]

📚 Gathering Notion context...
✅ Loaded Notion context

📥 Fetching epic details...
  ✅ CSSV-2045: Epic 1 Summary
  ✅ CSSV-2046: Epic 2 Summary
  ✅ CSSV-2047: Epic 3 Summary

🔧 Enriching 3 epics...

1. Processing CSSV-2045...
   Current: Epic 1 Summary
   📝 Enriching description...
   📅 Estimating duration...
   ✅ Estimated: 6 weeks
      Start: 2026-01-06
      End: 2026-02-17
   💾 Updating epic in Jira...
   ✅ Successfully updated CSSV-2045

...

📊 Summary
✅ Successfully updated: 3/3
```

## Manual Update (If Needed)

If the automatic update fails, you'll see instructions like:

```
📋 Manual update needed for CSSV-2045:
   Quarter: Q1 26
   Start Date: 2026-01-06
   End Date: 2026-02-17
   Description: [enriched description]
```

## Troubleshooting

### "No epics to process"
- Make sure you provided epic keys as arguments
- Verify the epic keys exist in Jira

### "Update error"
- Check that you have permission to edit the epics
- Verify the custom field IDs match your Jira instance
- The script will show what to update manually

### "Notion context not loading"
- Check your `NOTION_API_KEY` is set in `.env`
- Verify `NOTION_WORKSPACE_ID` is configured

## Notes

- The script uses **Gemini AI** to enrich descriptions and estimate durations
- It uses **Notion workspace** context for alignment with company goals
- Dates are estimated based on similar work patterns
- All dates are constrained to Q1 2026 (Jan 1 - Mar 31, 2026)













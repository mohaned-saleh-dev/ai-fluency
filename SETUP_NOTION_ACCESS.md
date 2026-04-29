# Setting Up Notion Access for Comprehensive PRD Generation

To create a PRD that accesses **ALL Notion resources** (all teams, squads, every single resource), you need to configure your Notion API key.

## Step 1: Get Your Notion API Key

1. Go to https://www.notion.so/my-integrations
2. Click **"New integration"**
3. Give it a name (e.g., "PRD Agent")
4. Select your workspace
5. Copy the **"Internal Integration Token"** - this is your `NOTION_API_KEY`

## Step 2: Share Resources with Integration

For the agent to access ALL resources, you need to share them with your integration:

### Share "My Space" folder:
1. Open "My Space" in Notion
2. Click the "..." menu (top right)
3. Select "Add connections"
4. Add your integration

### Share PRD Databases:
1. Open your "All PRDs" database/page
2. Click "..." → "Add connections"
3. Add your integration

### Share Tickets Database:
1. Open your "All Tickets" database
2. Click "..." → "Add connections"  
3. Add your integration

### Share Squad Priorities:
1. Open your squad priorities page
2. Click "..." → "Add connections"
3. Add your integration

## Step 3: Update .env File

Add your Notion API key to `/Users/mohaned.saleh/prd-ticket-agent/.env`:

```bash
NOTION_API_KEY=your_notion_api_key_here
NOTION_ALL_PRDS_PAGE_ID=your_all_prds_page_id
NOTION_ALL_TICKETS_PAGE_ID=your_all_tickets_page_id
NOTION_SQUAD_PRIORITIES_PAGE_ID=your_squad_priorities_page_id
```

## Step 4: Find Page IDs

To find page IDs:
1. Open the page in Notion
2. Look at the URL: `https://www.notion.so/Page-Name-abc123def456...`
3. The page ID is the part after the last dash (remove dashes)
4. Format: `abc123def456...` (32 characters, add dashes: `abc123de-f456-...`)

## Step 5: Run Comprehensive PRD Generator

Once configured, run:

```bash
python3 create_comprehensive_notion_prd.py <MY_SPACE_PAGE_ID>
```

This will:
- ✅ Access ALL PRDs in your database
- ✅ Access ALL tickets (2000+)
- ✅ Access squad priorities
- ✅ Fetch the related Unified Messaging PRD
- ✅ Generate comprehensive PRD with all context
- ✅ Include all diagrams and technical specs
- ✅ Create it in your Notion "My Space"

## Current Status

Right now, I've created comprehensive PRDs with:
- ✅ All mermaid diagrams (architecture, sequences, state machines, ERD)
- ✅ AI-generated technical specifications (using Gemini)
- ✅ AI-generated user journeys
- ✅ AI-generated API specifications
- ✅ Database schema with relationships
- ✅ Complete documentation

**Files created:**
- `PRD_In-App_Customer_Messaging_Inbox.docx` - Initial comprehensive version
- `PRD_In-App_Customer_Messaging_Inbox_COMPREHENSIVE.docx` - Enhanced with diagrams
- `PRD_In-App_Messaging_ULTIMATE.docx` - With Gemini-generated content

Once you configure Notion access, the PRD will be even more comprehensive by incorporating:
- Insights from all existing PRDs
- Patterns from 2000+ tickets
- Squad priorities and strategic context
- Technical details from related documentation




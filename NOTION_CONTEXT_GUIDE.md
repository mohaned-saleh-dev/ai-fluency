# How Notion Context Works

## Overview

The PRD Ticket Agent uses Notion as a knowledge base to ensure consistency, proper terminology, and alignment with your team's standards when creating PRDs and tickets.

## What Notion Resources Are Accessed?

The agent fetches three types of Notion resources:

### 1. **Squad Priorities** (`NOTION_SQUAD_PRIORITIES_PAGE_ID`)
- **What it is**: A Notion page containing your squad's priorities, success metrics, and strategic initiatives
- **How it's used**: 
  - Ensures PRDs align with squad goals
  - Includes the "why" behind projects
  - Sets appropriate success metrics
  - Links work to strategic objectives

### 2. **All PRDs Document** (`NOTION_ALL_PRDS_PAGE_ID`)
- **What it is**: A Notion page or database containing all existing PRDs
- **How it's used**:
  - Ensures format consistency (same structure, sections, icons)
  - Maintains tone and depth consistency
  - References similar projects for context
  - Follows established PRD patterns

### 3. **All Tickets Database** (`NOTION_ALL_TICKETS_PAGE_ID`)
- **What it is**: A Notion database with 2000+ existing tickets
- **How it's used**:
  - Learns correct terminology and naming conventions
  - Understands technical systems in use
  - Matches writing style and level of detail
  - Ensures technical alignment
  - Spots gaps and missing information

## How It Works - Step by Step

### When Creating a PRD:

```
1. User: "create prd for user authentication feature"
   ↓
2. Agent fetches from Notion:
   - Squad Priorities → Goals, success metrics, strategic context
   - All PRDs → Format, structure, tone examples
   - All Tickets → Terminology, technical systems, writing style
   ↓
3. Agent builds prompt with:
   - Your project description
   - Squad priorities (for alignment)
   - PRD format examples (for consistency)
   - Ticket terminology (for correct language)
   ↓
4. Gemini AI generates PRD using all this context
   ↓
5. PRD is created with proper:
   - Format matching existing PRDs
   - Terminology from existing tickets
   - Goals aligned with squad priorities
   - Success metrics matching CPX 2025
```

### When Creating a Ticket:

```
1. User: "create ticket for login UI"
   ↓
2. Agent fetches:
   - PRD content (from Notion or provided)
   - All Tickets database (2000+ tickets)
   - Related Jira issues (if Jira configured)
   ↓
3. Agent analyzes:
   - How similar tickets are written
   - Technical systems referenced
   - Acceptance criteria patterns
   - User story formats
   ↓
4. Ticket is generated with:
   - Consistent terminology
   - Proper technical references
   - Matching structure and style
   - Linked to PRD
```

## What Information Is Extracted?

### From Squad Priorities:
- Strategic goals and objectives
- Success metrics (CPX 2025 alignment)
- Key initiatives
- Priority areas

### From All PRDs:
- Section structure (Introduction, Problem, Goals, etc.)
- Formatting style (icons, headings, lists)
- Depth and detail level
- Tone and writing style

### From All Tickets:
- Technical terminology (system names, components)
- Writing patterns (how user stories are phrased)
- Acceptance criteria formats
- Technical system references
- Common patterns and conventions

## Configuration

Set these environment variables in your `.env` file:

```bash
# Notion API Key (required for Notion integration)
NOTION_API_KEY=your_notion_api_key

# Squad Priorities Page ID
NOTION_SQUAD_PRIORITIES_PAGE_ID=your_page_id

# All PRDs Page/Database ID
NOTION_ALL_PRDS_PAGE_ID=your_page_id

# All Tickets Database ID
NOTION_ALL_TICKETS_PAGE_ID=your_database_id
```

## How to Get Notion Page/Database IDs

1. **Open the Notion page/database**
2. **Click "..." menu** → **"Copy link"**
3. **Extract the ID** from the URL:
   ```
   https://www.notion.so/Your-Page-abc123def456...
                                    ^^^^^^^^^^^^
                                    This is the ID (32 characters)
   ```
4. **Remove hyphens** from the ID when setting in `.env`

## Example: What Gets Included in the Prompt

When you create a PRD, the agent builds a prompt like this:

```
You are creating a PRD for: [your project description]

## Squad Priorities and Context
[Content from your squad priorities page]
- Strategic goal: Increase user engagement
- Success metric: 20% increase in DAU
- Priority: Q1 2025

## Reference: All PRDs Format
Review similar PRDs to ensure consistency in structure, tone, and depth.

## Reference: All Tickets (2000+ tickets)
Review existing tickets for terminology, technical systems, and writing style.
- System names: "Payment Gateway", "User Service"
- Terminology: "customer" not "user", "order" not "transaction"
- Patterns: User stories follow "As a [role], I want [goal] so that [benefit]"

## Instructions
- Align with squad priorities
- Follow PRD format from examples
- Use correct terminology from tickets
- Match writing style
...
```

## Benefits

✅ **Consistency**: All PRDs and tickets follow the same format and style
✅ **Terminology**: Uses correct technical terms and system names
✅ **Alignment**: Links work to strategic goals and priorities
✅ **Quality**: References 2000+ existing tickets for patterns
✅ **Context**: Understands your technical architecture and systems

## What If Notion Isn't Configured?

The agent will still work, but:
- ⚠️ Won't have squad priorities context
- ⚠️ Won't reference existing PRD formats
- ⚠️ Won't learn from existing tickets
- ✅ Will still create PRDs/tickets (just without the context)

## Troubleshooting

**"Error fetching squad priorities"**
- Check that `NOTION_SQUAD_PRIORITIES_PAGE_ID` is correct
- Verify the page is accessible with your API key
- Make sure the page ID has no hyphens

**"Error fetching All Tickets"**
- Verify `NOTION_ALL_TICKETS_PAGE_ID` is a database ID (not page ID)
- Check database permissions
- Ensure API key has access

**"No context found"**
- Verify `NOTION_API_KEY` is set correctly
- Check that page/database IDs are correct
- Test API key: `curl -H "Authorization: Bearer YOUR_KEY" https://api.notion.com/v1/users/me`













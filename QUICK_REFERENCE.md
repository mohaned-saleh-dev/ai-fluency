# Quick Reference Card

## PRD Ticket Agent - Command Reference

### Installation

```bash
cd prd-ticket-agent
pip install -e .
```

### Basic Commands

#### Create a PRD

```bash
# Simple usage
prd-agent prd --description "Your project description"

# From file
prd-agent prd --file description.txt

# JSON output
prd-agent prd --description "Project" --format json

# Custom config
prd-agent prd --description "Project" --config config.json
```

#### Create a Jira Ticket

```bash
# With PRD from Notion
prd-agent ticket --prd-id "notion_id" --project PROJ --description "Ticket description"

# With PRD JSON file
prd-agent ticket --prd-file prd.json --project PROJ --description "Ticket description"
```

### Required Environment Variables

**Minimum required:**
```bash
GEMINI_API_KEY=your_key_here
```

**Full configuration:**
```bash
# Gemini AI
GEMINI_API_KEY=your_key
GEMINI_MODEL_NAME=gemini-2.5-pro  # Optional

# Notion (optional but recommended)
NOTION_API_KEY=your_key
NOTION_PRD_DATABASE_ID=your_id
NOTION_TICKETS_DATABASE_ID=your_id
NOTION_ALL_PRDS_PAGE_ID=your_id
NOTION_ALL_TICKETS_PAGE_ID=your_id
NOTION_SQUAD_PRIORITIES_PAGE_ID=your_id

# Jira (optional, needed for ticket creation)
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your_email@company.com
JIRA_API_TOKEN=your_token
```

### Help

```bash
prd-agent --help
prd-agent prd --help
prd-agent ticket --help
```

### Common Issues

**Command not found:**
- Make sure you installed with `pip install -e .`
- Check your PATH includes Python's bin directory
- Try: `python -m prd_ticket_agent.cli prd --help`

**API Key error:**
- Verify: `echo $GEMINI_API_KEY`
- Set in `.env` file or export in shell

**Import errors:**
- Run: `pip install -r requirements.txt`













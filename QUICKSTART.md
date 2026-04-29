# Quick Start Guide

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the agent:**

   Create a `.env` file or set environment variables:
   ```bash
   # Required for Notion integration
   export NOTION_API_KEY="your_notion_api_key"
   export NOTION_ALL_PRDS_PAGE_ID="your_all_prds_page_id"
   export NOTION_ALL_TICKETS_PAGE_ID="your_all_tickets_page_id"
   export NOTION_SQUAD_PRIORITIES_PAGE_ID="your_squad_priorities_page_id"
   
   # Required for Jira integration
   export JIRA_URL="https://your-company.atlassian.net"
   export JIRA_EMAIL="your_email@company.com"
   export JIRA_API_TOKEN="your_jira_api_token"
   
   # Required for Gemini LLM
   export GEMINI_API_KEY="your_gemini_api_key"
   export GEMINI_MODEL_NAME="gemini-pro"  # Optional, defaults to "gemini-pro"
   
   # Optional
   export AI_CHATBOT_CSV_PATH="path/to/ai_chatbot_requirements.csv"
   ```

## Getting Notion API Credentials

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Give it a name and select your workspace
4. Copy the "Internal Integration Token" - this is your `NOTION_API_KEY`
5. Share your Notion pages/databases with this integration

## Getting Jira API Credentials

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token - this is your `JIRA_API_TOKEN`
4. Use your email as `JIRA_EMAIL`

## Getting Gemini API Credentials

1. Go to https://makersuite.google.com/app/apikey or https://aistudio.google.com/app/apikey
2. Click "Create API Key" or "Get API Key"
3. Copy the API key - this is your `GEMINI_API_KEY`
4. The agent uses `gemini-pro` by default, but you can specify a different model with `GEMINI_MODEL_NAME`

## Finding Notion Page IDs

1. Open the Notion page in your browser
2. The URL will look like: `https://www.notion.so/Your-Page-Name-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
3. The page ID is the last part: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
4. Remove dashes: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

## Usage Examples

### Create a PRD

```bash
python cli.py prd --description "Add user authentication feature"
```

### Create a PRD from a file

```bash
python cli.py prd --file project_description.txt
```

### Create a Jira ticket

```bash
python cli.py ticket \
  --prd-id "notion_page_id_here" \
  --project PROJ \
  --description "Implement login UI"
```

### Using Python API

```python
import asyncio
from prd_ticket_agent import PRDTicketAgent, AgentContext
from prd_ticket_agent.config import load_context_from_env

async def main():
    # Load from environment variables
    context = load_context_from_env()
    agent = PRDTicketAgent(context)
    
    # Create PRD
    prd = await agent.create_prd(
        project_description="Add user authentication feature"
    )
    print(prd)

asyncio.run(main())
```

## Next Steps

- Review the `README.md` for detailed documentation
- Check `example_usage.py` for more examples
- Read `INSTRUCTIONS.md` to understand the agent's behavior


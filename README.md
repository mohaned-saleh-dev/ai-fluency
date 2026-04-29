# PRD and Jira Ticket Writing Agent

A focused, installable application for creating Product Requirements Documents (PRDs) and Jira tickets using AI. This agent is dedicated exclusively to PRD and ticket generation, powered by Google's Gemini AI.

## Features

- **PRD Generation**: Creates comprehensive PRDs following your team's format and style using Gemini LLM
- **Jira Ticket Creation**: Generates tickets linked to PRDs with proper structure using Gemini LLM
- **Gemini LLM Integration**: Powered by Google's Gemini for intelligent content generation
- **Notion Integration**: Accesses squad priorities, existing PRDs, and tickets for context
- **Style Guide Enforcement**: Ensures consistent, natural writing style
- **Context Awareness**: Reviews 2000+ existing tickets for terminology and consistency
- **AI Chatbot Support**: Special handling for AI Chatbot-related work
- **Installable App**: Install as a standalone command-line application

## Quick Installation

### Install as an App

```bash
# Navigate to the project directory
cd prd-ticket-agent

# Install the package
pip install -e .

# Verify installation
prd-agent --help
```

The `prd-agent` command will be available system-wide after installation.

For detailed installation instructions, see [INSTALL.md](INSTALL.md).

## Quick Start

1. **Set up your API key:**
   ```bash
   export GEMINI_API_KEY="your_gemini_api_key"
   ```

2. **Create a PRD:**
   ```bash
   prd-agent prd --description "Add user authentication feature"
   ```

3. **Create a Jira ticket:**
   ```bash
   prd-agent ticket --prd-file prd.json --project PROJ --description "Implement login UI"
   ```

## Configuration

### Option 1: Environment Variables

Set the following environment variables:

```bash
export NOTION_API_KEY="your_notion_api_key"
export JIRA_URL="https://your-company.atlassian.net"
export JIRA_EMAIL="your_email@company.com"
export JIRA_API_TOKEN="your_jira_api_token"
export NOTION_PRD_DATABASE_ID="your_prd_database_id"
export NOTION_TICKETS_DATABASE_ID="your_tickets_database_id"
export NOTION_ALL_PRDS_PAGE_ID="your_all_prds_page_id"
export NOTION_ALL_TICKETS_PAGE_ID="your_all_tickets_page_id"
export NOTION_SQUAD_PRIORITIES_PAGE_ID="your_squad_priorities_page_id"
export AI_CHATBOT_CSV_PATH="path/to/ai_chatbot_requirements.csv"
export GEMINI_API_KEY="your_gemini_api_key"
export GEMINI_MODEL_NAME="gemini-pro"  # Optional, defaults to "gemini-pro"
```

### Option 2: Configuration File

Create a `config.json` file:

```json
{
  "notion_api_key": "your_notion_api_key",
  "jira_url": "https://your-company.atlassian.net",
  "jira_email": "your_email@company.com",
  "jira_api_token": "your_jira_api_token",
  "notion_prd_database_id": "your_prd_database_id",
  "notion_tickets_database_id": "your_tickets_database_id",
  "notion_all_prds_page_id": "your_all_prds_page_id",
  "notion_all_tickets_page_id": "your_all_tickets_page_id",
  "notion_squad_priorities_page_id": "your_squad_priorities_page_id",
  "ai_chatbot_csv_path": "path/to/ai_chatbot_requirements.csv",
  "gemini_api_key": "your_gemini_api_key",
  "gemini_model_name": "gemini-pro"
}
```

## Usage

### Command Line Interface

After installation, use the `prd-agent` command:

#### Create a PRD

```bash
# Using description directly
prd-agent prd --description "Add user authentication feature"

# Using a file
prd-agent prd --file project_description.txt

# With custom config
prd-agent prd --description "Feature X" --config my_config.json

# JSON output
prd-agent prd --description "Feature X" --format json
```

#### Create a Jira Ticket

```bash
# With PRD ID from Notion
prd-agent ticket --prd-id "notion_page_id" --project PROJ --description "Implement login UI"

# With PRD JSON file
prd-agent ticket --prd-file prd.json --project PROJ --description "Implement login UI"

# With custom config
prd-agent ticket --prd-id "notion_page_id" --project PROJ --config my_config.json
```

**Note:** If you haven't installed the package, you can still use `python cli.py` instead of `prd-agent`.

### Python API

```python
from prd_ticket_agent import PRDTicketAgent, AgentContext
import asyncio

# Set up context
context = AgentContext(
    notion_api_key="your_key",
    jira_url="https://your-company.atlassian.net",
    # ... other config
)

# Initialize agent
agent = PRDTicketAgent(context)

# Create a PRD
async def main():
    prd = await agent.create_prd(
        project_description="Add user authentication feature"
    )
    print(prd)

asyncio.run(main())
```

## PRD Structure

Each PRD includes the following sections:

- 📌 Introduction
- ❗ Problem Statement
- 🎯 Goals
- 📊 Success Metrics (must align with CPX 2025)
- 👤 User Personas
- 💡 Solution
- 📐 Solution Design
- ✅ Inclusions and Exclusions
- 🚀 Roll-out Plan

## Ticket Structure

Each Jira ticket includes:

- 🧑‍💻 User Story
- ✅ Acceptance Criteria
- 📝 Description

## Writing Style Guide

The agent enforces a natural, clear writing style:

- ✅ Plain, simple language
- ✅ Concise and direct
- ✅ Natural tone
- ❌ No AI clichés
- ❌ No marketing fluff
- ❌ No verbose phrases

## How It Works

1. **Context Gathering**: The agent accesses Notion to gather:
   - Squad priorities and success metrics
   - Existing PRD formats for consistency
   - All tickets (2000+) for terminology and style

2. **PRD Generation**: 
   - Aligns with squad priorities
   - Follows established PRD format
   - Uses correct terminology from existing tickets
   - Applies writing style guide

3. **Ticket Creation**:
   - Links to PRD
   - Matches existing ticket structure and style
   - Ensures technical alignment
   - Cross-references all tickets for consistency

## Special Cases

### AI Chatbot Work

If the project involves AI Chatbot functionality, the agent automatically:
- References the AI Chatbot Functional Requirements CSV
- Ensures alignment with chatbot requirements
- Uses appropriate terminology

## About This Agent

This is a **focused PRD and Ticket Writing Agent** dedicated exclusively to:
- Creating Product Requirements Documents (PRDs)
- Generating Jira tickets linked to PRDs

**Note:** This agent does not include Slack management functionality. It is purpose-built for PRD and ticket creation workflows.

## Development

### Project Structure

```
prd_ticket_agent/
├── __init__.py              # Package exports (PRD agent only)
├── agent.py                 # Main PRD ticket agent orchestrator
├── prd_generator.py         # PRD generation logic
├── ticket_generator.py      # Ticket generation logic
├── prompts.py               # Prompt templates
├── style_guide.py           # Style guide enforcement
├── config.py                # Configuration management
└── integrations/
    ├── __init__.py
    ├── notion_client.py     # Notion API client
    ├── jira_client.py       # Jira API client
    └── gemini_client.py     # Gemini AI client
```

## Requirements

- Python 3.8+
- Notion API access
- Jira API access (for ticket creation)

## License

[Your License Here]

## Contributing

[Contributing Guidelines]


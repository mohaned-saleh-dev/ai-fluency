"""
Configuration management for the agent.
"""

import os
from typing import Optional
from pathlib import Path
from .agent import AgentContext

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, manually load .env file
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value


def load_context_from_env() -> AgentContext:
    """
    Load agent context from environment variables.
    
    Environment variables:
    - NOTION_API_KEY: Notion API key
    - JIRA_URL: Jira instance URL
    - JIRA_EMAIL: Jira user email
    - JIRA_API_TOKEN: Jira API token
    - NOTION_PRD_DATABASE_ID: Notion database ID for PRDs
    - NOTION_TICKETS_DATABASE_ID: Notion database ID for tickets
    - NOTION_ALL_PRDS_PAGE_ID: Notion page ID for "All PRDs" document
    - NOTION_ALL_TICKETS_PAGE_ID: Notion page ID for "All Tickets" document
    - NOTION_WORKSPACE_ID: Notion workspace/space page ID (e.g., from https://notion.so/workspace/Agent-xxx)
    - AI_CHATBOT_CSV_PATH: Path to AI Chatbot Functional Requirements CSV
    - GEMINI_API_KEY: Google Gemini API key
    - GEMINI_MODEL_NAME: Gemini model name (default: "gemini-2.5-pro")
    """
    # Default to Agent workspace if not specified
    workspace_id = os.getenv("NOTION_WORKSPACE_ID", "13662429127880a291deebd5d0fdb130")
    
    return AgentContext(
        notion_api_key=os.getenv("NOTION_API_KEY"),
        jira_url=os.getenv("JIRA_URL"),
        jira_email=os.getenv("JIRA_EMAIL"),
        jira_api_token=os.getenv("JIRA_API_TOKEN"),
        notion_prd_database_id=os.getenv("NOTION_PRD_DATABASE_ID"),
        notion_tickets_database_id=os.getenv("NOTION_TICKETS_DATABASE_ID"),
        notion_all_prds_page_id=os.getenv("NOTION_ALL_PRDS_PAGE_ID"),
        notion_all_tickets_page_id=os.getenv("NOTION_ALL_TICKETS_PAGE_ID"),
        notion_squad_priorities_page_id=os.getenv("NOTION_SQUAD_PRIORITIES_PAGE_ID"),
        notion_workspace_id=workspace_id,
        ai_chatbot_csv_path=os.getenv("AI_CHATBOT_CSV_PATH"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model_name=os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-pro")
    )


def load_context_from_file(config_path: str = "config.json") -> AgentContext:
    """
    Load agent context from a JSON configuration file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        AgentContext object
    """
    import json
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return AgentContext(
        notion_api_key=config.get("notion_api_key"),
        jira_url=config.get("jira_url"),
        jira_email=config.get("jira_email"),
        jira_api_token=config.get("jira_api_token"),
        notion_prd_database_id=config.get("notion_prd_database_id"),
        notion_tickets_database_id=config.get("notion_tickets_database_id"),
        notion_all_prds_page_id=config.get("notion_all_prds_page_id"),
        notion_all_tickets_page_id=config.get("notion_all_tickets_page_id"),
        notion_squad_priorities_page_id=config.get("notion_squad_priorities_page_id"),
        notion_workspace_id=config.get("notion_workspace_id", "13662429127880a291deebd5d0fdb130"),
        ai_chatbot_csv_path=config.get("ai_chatbot_csv_path"),
        gemini_api_key=config.get("gemini_api_key"),
        gemini_model_name=config.get("gemini_model_name", "gemini-2.5-pro")
    )


"""
PRD and Jira Ticket Writing Agent
Main agent orchestrator that handles PRD and ticket creation requests.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Types of tasks the agent can handle."""
    CREATE_PRD = "create_prd"
    CREATE_TICKET = "create_ticket"
    REVIEW_PRD = "review_prd"
    REVIEW_TICKET = "review_ticket"


@dataclass
class AgentContext:
    """Context information for the agent."""
    notion_api_key: Optional[str] = None
    jira_url: Optional[str] = None
    jira_email: Optional[str] = None
    jira_api_token: Optional[str] = None
    notion_prd_database_id: Optional[str] = None
    notion_tickets_database_id: Optional[str] = None
    notion_all_prds_page_id: Optional[str] = None
    notion_all_tickets_page_id: Optional[str] = None
    notion_squad_priorities_page_id: Optional[str] = None
    notion_workspace_id: Optional[str] = None  # Workspace/space page ID to scan
    ai_chatbot_csv_path: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model_name: str = "gemini-2.5-pro"


class PRDTicketAgent:
    """
    Main agent for creating PRDs and Jira tickets.
    
    This agent:
    - Accesses Notion documents for context
    - Creates PRDs following the specified format
    - Creates Jira tickets linked to PRDs
    - References existing PRDs and tickets for consistency
    - Follows the writing style guide
    """
    
    def __init__(self, context: AgentContext):
        self.context = context
        self.notion_client = None
        self.jira_client = None
        self._initialize_clients()
        
    def _initialize_clients(self):
        """Initialize Notion and Jira clients."""
        if self.context.notion_api_key:
            from .integrations.notion_client import NotionClient
            self.notion_client = NotionClient(self.context.notion_api_key)
        
        if self.context.jira_url and self.context.jira_email and self.context.jira_api_token:
            from .integrations.jira_client import JiraClient
            self.jira_client = JiraClient(
                self.context.jira_url,
                self.context.jira_email,
                self.context.jira_api_token
            )
    
    async def create_prd(
        self,
        project_description: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a PRD based on the project description.
        
        Args:
            project_description: Description of the project/feature
            additional_context: Any additional context from the user
            
        Returns:
            Dictionary containing the PRD content and metadata
        """
        from .prd_generator import PRDGenerator
        
        generator = PRDGenerator(
            notion_client=self.notion_client,
            context=self.context,
            jira_client=self.jira_client
        )
        
        prd = await generator.generate(
            project_description=project_description,
            additional_context=additional_context or {}
        )
        
        return prd
    
    async def create_ticket(
        self,
        prd_id: Optional[str] = None,
        prd_content: Optional[Dict[str, Any]] = None,
        ticket_description: Optional[str] = None,
        project_key: str = None
    ) -> Dict[str, Any]:
        """
        Create a Jira ticket linked to a PRD.
        
        Args:
            prd_id: ID of the PRD in Notion (if exists)
            prd_content: PRD content dictionary (if PRD not in Notion yet)
            ticket_description: Description of the specific ticket
            project_key: Jira project key (e.g., 'PROJ')
            
        Returns:
            Dictionary containing the ticket content and metadata
        """
        if not prd_id and not prd_content:
            raise ValueError(
                "Either prd_id or prd_content must be provided. "
                "Please provide a PRD before creating tickets."
            )
        
        from .ticket_generator import TicketGenerator
        
        generator = TicketGenerator(
            notion_client=self.notion_client,
            jira_client=self.jira_client,
            context=self.context
        )
        
        ticket = await generator.generate(
            prd_id=prd_id,
            prd_content=prd_content,
            ticket_description=ticket_description,
            project_key=project_key
        )
        
        return ticket
    
    async def get_context_from_notion(self) -> Dict[str, Any]:
        """
        Retrieve context from Notion including:
        - Squad priorities and success metrics
        - All PRDs format reference
        - All tickets for terminology and consistency
        """
        if not self.notion_client:
            return {}
        
        context = {}
        
        # Get squad priorities
        if self.context.notion_squad_priorities_page_id:
            context['squad_priorities'] = await self.notion_client.get_page_content(
                self.context.notion_squad_priorities_page_id
            )
        
        # Get All PRDs document
        if self.context.notion_all_prds_page_id:
            context['all_prds'] = await self.notion_client.get_page_content(
                self.context.notion_all_prds_page_id
            )
        
        # Get All Tickets document
        if self.context.notion_all_tickets_page_id:
            context['all_tickets'] = await self.notion_client.get_database_entries(
                self.context.notion_all_tickets_page_id
            )
        
        return context
    
    async def reference_ai_chatbot_requirements(self) -> Optional[Dict[str, Any]]:
        """Load AI Chatbot Functional Requirements if available."""
        if not self.context.ai_chatbot_csv_path:
            return None
        
        import csv
        requirements = {}
        
        if os.path.exists(self.context.ai_chatbot_csv_path):
            with open(self.context.ai_chatbot_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                requirements = list(reader)
        
        return requirements


"""
Jira API client for creating and managing tickets.
"""

from typing import Dict, List, Optional, Any
import httpx
from base64 import b64encode


class JiraClient:
    """Client for interacting with Jira API."""
    
    def __init__(self, jira_url: str, email: str, api_token: str):
        self.jira_url = jira_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        
        # Create basic auth header
        credentials = b64encode(f"{email}:{api_token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json"
        }
    
    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Story",
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Jira issue.
        
        Args:
            project_key: Jira project key (e.g., 'PROJ')
            summary: Issue summary/title
            description: Issue description
            issue_type: Type of issue (Story, Task, Bug, etc.)
            additional_fields: Any additional fields to set
            
        Returns:
            Created issue data
        """
        async with httpx.AsyncClient() as client:
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": issue_type}
                }
            }
            
            if additional_fields:
                payload["fields"].update(additional_fields)
            
            response = await client.post(
                f"{self.jira_url}/rest/api/3/issue",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Retrieve a Jira issue.
        
        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123')
            
        Returns:
            Issue data
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.jira_url}/rest/api/3/issue/{issue_key}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def search_issues(
        self,
        jql: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for Jira issues using JQL.
        
        Args:
            jql: Jira Query Language query
            max_results: Maximum number of results
            
        Returns:
            List of matching issues
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.jira_url}/rest/api/3/search",
                headers=self.headers,
                json={
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": ["summary", "description", "status", "issuetype"]
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("issues", [])
    
    def format_description(self, content: Dict[str, Any]) -> str:
        """
        Format content as Jira description using ADF (Atlassian Document Format).
        
        Args:
            content: Dictionary with structured content
            
        Returns:
            ADF-formatted description string
        """
        # For simplicity, we'll use a basic ADF structure
        # In production, you'd want a more robust formatter
        adf = {
            "version": 1,
            "type": "doc",
            "content": []
        }
        
        # Convert markdown-like structure to ADF
        # This is a simplified version - you'd want a full markdown to ADF converter
        if isinstance(content, dict):
            for key, value in content.items():
                if key == "user_story":
                    adf["content"].append({
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "User Story"}]
                    })
                    adf["content"].append({
                        "type": "paragraph",
                        "content": [{"type": "text", "text": str(value)}]
                    })
                elif key == "acceptance_criteria":
                    adf["content"].append({
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "Acceptance Criteria"}]
                    })
                    if isinstance(value, list):
                        for item in value:
                            adf["content"].append({
                                "type": "bulletList",
                                "content": [{
                                    "type": "listItem",
                                    "content": [{
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": str(item)}]
                                    }]
                                }]
                            })
        
        import json
        return json.dumps(adf)




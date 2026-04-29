"""
Notion API client for accessing documents and databases.
"""

import os
from typing import Dict, List, Optional, Any
import httpx


class NotionClient:
    """Client for interacting with Notion API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    
    async def get_page_content(self, page_id: str) -> Dict[str, Any]:
        """
        Retrieve content from a Notion page.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            Page content as dictionary
        """
        async with httpx.AsyncClient() as client:
            # Get page
            response = await client.get(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers
            )
            response.raise_for_status()
            page_data = response.json()
            
            # Get page blocks/content
            blocks_response = await client.get(
                f"{self.base_url}/blocks/{page_id}/children",
                headers=self.headers
            )
            blocks_response.raise_for_status()
            blocks_data = blocks_response.json()
            
            return {
                "page": page_data,
                "blocks": blocks_data.get("results", [])
            }
    
    async def get_database_entries(
        self,
        database_id: str,
        filter_conditions: Optional[Dict[str, Any]] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve entries from a Notion database.
        
        Args:
            database_id: Notion database ID
            filter_conditions: Optional filter conditions
            max_results: Maximum number of results to retrieve
            
        Returns:
            List of database entries
        """
        async with httpx.AsyncClient() as client:
            all_results = []
            has_more = True
            start_cursor = None
            
            while has_more and len(all_results) < max_results:
                payload = {
                    "page_size": min(100, max_results - len(all_results))
                }
                
                if start_cursor:
                    payload["start_cursor"] = start_cursor
                
                if filter_conditions:
                    payload["filter"] = filter_conditions
                
                response = await client.post(
                    f"{self.base_url}/databases/{database_id}/query",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                all_results.extend(data.get("results", []))
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
            
            return all_results
    
    async def create_page(
        self,
        parent_database_id: str,
        properties: Dict[str, Any],
        content_blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create a new page in a Notion database.
        
        Args:
            parent_database_id: ID of the parent database
            properties: Page properties
            content_blocks: Optional content blocks for the page
            
        Returns:
            Created page data
        """
        async with httpx.AsyncClient() as client:
            payload = {
                "parent": {"database_id": parent_database_id},
                "properties": properties
            }
            
            response = await client.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            page_data = response.json()
            
            # Add content blocks if provided
            if content_blocks and page_data.get("id"):
                await self._add_blocks_to_page(page_data["id"], content_blocks)
            
            return page_data
    
    async def _add_blocks_to_page(
        self,
        page_id: str,
        blocks: List[Dict[str, Any]]
    ):
        """Add content blocks to a page."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/blocks/{page_id}/children",
                headers=self.headers,
                json={"children": blocks}
            )
            response.raise_for_status()
    
    def extract_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """
        Extract plain text from Notion blocks.
        
        Args:
            blocks: List of Notion block objects
            
        Returns:
            Plain text content
        """
        text_parts = []
        
        for block in blocks:
            block_type = block.get("type")
            if block_type == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                text_parts.append(self._extract_rich_text(rich_text))
            elif block_type == "heading_1":
                rich_text = block.get("heading_1", {}).get("rich_text", [])
                text_parts.append(f"# {self._extract_rich_text(rich_text)}")
            elif block_type == "heading_2":
                rich_text = block.get("heading_2", {}).get("rich_text", [])
                text_parts.append(f"## {self._extract_rich_text(rich_text)}")
            elif block_type == "heading_3":
                rich_text = block.get("heading_3", {}).get("rich_text", [])
                text_parts.append(f"### {self._extract_rich_text(rich_text)}")
            elif block_type == "bulleted_list_item":
                rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
                text_parts.append(f"- {self._extract_rich_text(rich_text)}")
            elif block_type == "numbered_list_item":
                rich_text = block.get("numbered_list_item", {}).get("rich_text", [])
                text_parts.append(f"1. {self._extract_rich_text(rich_text)}")
            elif block_type == "to_do":
                rich_text = block.get("to_do", {}).get("rich_text", [])
                checked = block.get("to_do", {}).get("checked", False)
                checkbox = "[x]" if checked else "[ ]"
                text_parts.append(f"{checkbox} {self._extract_rich_text(rich_text)}")
        
        return "\n\n".join(text_parts)
    
    def _extract_rich_text(self, rich_text: List[Dict[str, Any]]) -> str:
        """Extract plain text from Notion rich text array."""
        return "".join([item.get("plain_text", "") for item in rich_text])
    
    async def search_workspace(
        self,
        query: str,
        max_results: int = 20,
        filter_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the entire Notion workspace for pages and databases.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            filter_type: Optional filter by type ('page' or 'database')
            
        Returns:
            List of search results (pages and databases)
        """
        async with httpx.AsyncClient() as client:
            all_results = []
            has_more = True
            start_cursor = None
            
            while has_more and len(all_results) < max_results:
                payload = {
                    "query": query,
                    "page_size": min(100, max_results - len(all_results))
                }
                
                if start_cursor:
                    payload["start_cursor"] = start_cursor
                
                if filter_type:
                    payload["filter"] = {"value": filter_type, "property": "object"}
                
                response = await client.post(
                    f"{self.base_url}/search",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                all_results.extend(data.get("results", []))
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
            
            return all_results
    
    async def get_all_pages_from_space(self, max_results: int = 1000) -> List[Dict[str, Any]]:
        """
        Get all pages from the workspace (My Space).
        
        Args:
            max_results: Maximum number of pages to retrieve
            
        Returns:
            List of all pages
        """
        return await self.search_workspace("", max_results=max_results, filter_type="page")
    
    async def extract_knowledge_base(
        self,
        page_ids: Optional[List[str]] = None,
        max_pages: int = 100
    ) -> str:
        """
        Extract knowledge base from Notion pages.
        
        Args:
            page_ids: Optional list of specific page IDs to extract
            max_pages: Maximum number of pages to process if page_ids not provided
            
        Returns:
            Combined text content from all pages
        """
        knowledge_parts = []
        
        if page_ids:
            pages_to_process = page_ids
        else:
            # Get all pages from workspace
            all_pages = await self.get_all_pages_from_space(max_results=max_pages)
            pages_to_process = [page["id"] for page in all_pages[:max_pages]]
        
        for page_id in pages_to_process:
            try:
                page_content = await self.get_page_content(page_id)
                page_title = page_content.get("page", {}).get("properties", {}).get("title", {})
                title_text = self._extract_rich_text(
                    page_title.get("title", []) if isinstance(page_title, dict) else []
                )
                
                blocks_text = self.extract_text_from_blocks(page_content.get("blocks", []))
                
                if title_text or blocks_text:
                    knowledge_parts.append(f"=== {title_text or 'Untitled Page'} ===\n{blocks_text}\n")
            except Exception as e:
                # Skip pages that can't be accessed
                continue
        
        return "\n\n".join(knowledge_parts)


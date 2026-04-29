#!/usr/bin/env python3
"""
Fetch Zendesk-Salesforce Transition Plan from Notion and extract rollout data.
"""

import os
import json
import httpx
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

# Notion page ID from the URL
PAGE_ID = "2e162429127880f68d95f71c97856b60"

class NotionFetcher:
    """Fetch content from Notion API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        self.all_content = []
    
    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page metadata."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_blocks(self, block_id: str, start_cursor: Optional[str] = None) -> Dict[str, Any]:
        """Get blocks (children) of a block/page."""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/blocks/{block_id}/children"
            params = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor
            
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
    
    async def get_all_blocks_recursive(self, block_id: str, depth: int = 0) -> List[Dict[str, Any]]:
        """Recursively get all blocks including nested ones."""
        all_blocks = []
        has_more = True
        start_cursor = None
        
        while has_more:
            data = await self.get_blocks(block_id, start_cursor)
            blocks = data.get("results", [])
            
            for block in blocks:
                block["_depth"] = depth
                all_blocks.append(block)
                
                # Recursively get children if this block has children
                if block.get("has_children", False):
                    children = await self.get_all_blocks_recursive(block["id"], depth + 1)
                    all_blocks.extend(children)
            
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
        
        return all_blocks
    
    def extract_text(self, rich_text: List[Dict[str, Any]]) -> str:
        """Extract plain text from rich text array."""
        return "".join([item.get("plain_text", "") for item in rich_text])
    
    def extract_table_data(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract all tables from the blocks."""
        tables = []
        current_table = None
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type == "table":
                current_table = {
                    "id": block["id"],
                    "has_column_header": block.get("table", {}).get("has_column_header", False),
                    "has_row_header": block.get("table", {}).get("has_row_header", False),
                    "rows": []
                }
                tables.append(current_table)
            
            elif block_type == "table_row":
                cells = block.get("table_row", {}).get("cells", [])
                row_data = [self.extract_text(cell) for cell in cells]
                
                # Find which table this row belongs to (last table in the list)
                if tables:
                    tables[-1]["rows"].append(row_data)
        
        return tables
    
    def parse_blocks_to_text(self, blocks: List[Dict[str, Any]]) -> str:
        """Parse blocks to readable text format."""
        output = []
        
        for block in blocks:
            block_type = block.get("type")
            depth = block.get("_depth", 0)
            indent = "  " * depth
            
            if block_type == "heading_1":
                text = self.extract_text(block.get("heading_1", {}).get("rich_text", []))
                output.append(f"\n{'='*60}\n# {text}\n{'='*60}")
            
            elif block_type == "heading_2":
                text = self.extract_text(block.get("heading_2", {}).get("rich_text", []))
                output.append(f"\n## {text}")
            
            elif block_type == "heading_3":
                text = self.extract_text(block.get("heading_3", {}).get("rich_text", []))
                output.append(f"\n### {text}")
            
            elif block_type == "paragraph":
                text = self.extract_text(block.get("paragraph", {}).get("rich_text", []))
                if text:
                    output.append(f"{indent}{text}")
            
            elif block_type == "bulleted_list_item":
                text = self.extract_text(block.get("bulleted_list_item", {}).get("rich_text", []))
                output.append(f"{indent}• {text}")
            
            elif block_type == "numbered_list_item":
                text = self.extract_text(block.get("numbered_list_item", {}).get("rich_text", []))
                output.append(f"{indent}1. {text}")
            
            elif block_type == "toggle":
                text = self.extract_text(block.get("toggle", {}).get("rich_text", []))
                output.append(f"{indent}▸ {text}")
            
            elif block_type == "table":
                output.append(f"\n{indent}[TABLE]")
            
            elif block_type == "table_row":
                cells = block.get("table_row", {}).get("cells", [])
                row_data = [self.extract_text(cell) for cell in cells]
                output.append(f"{indent}| {' | '.join(row_data)} |")
            
            elif block_type == "callout":
                text = self.extract_text(block.get("callout", {}).get("rich_text", []))
                icon = block.get("callout", {}).get("icon", {}).get("emoji", "📌")
                output.append(f"{indent}{icon} {text}")
            
            elif block_type == "divider":
                output.append(f"{indent}---")
        
        return "\n".join(output)


async def fetch_and_save():
    """Main function to fetch Notion content and save it."""
    
    # Try to get API key from environment or ask user
    api_key = os.environ.get("NOTION_API_KEY")
    
    if not api_key or api_key == "your_notion_api_key_here":
        print("=" * 60)
        print("NOTION API KEY REQUIRED")
        print("=" * 60)
        print("\nPlease enter your Notion API key.")
        print("You can get it from: https://www.notion.so/my-integrations")
        print()
        api_key = input("Notion API Key: ").strip()
        
        if not api_key:
            print("No API key provided. Exiting.")
            return
    
    print(f"\nFetching Notion page: {PAGE_ID}")
    print("This may take a moment...\n")
    
    fetcher = NotionFetcher(api_key)
    
    try:
        # Get page metadata
        page = await fetcher.get_page(PAGE_ID)
        title = fetcher.extract_text(
            page.get("properties", {}).get("title", {}).get("title", [])
        )
        print(f"Page Title: {title or 'Zendesk-Salesforce Transition Plan'}")
        
        # Get all blocks recursively
        print("Fetching all content blocks...")
        blocks = await fetcher.get_all_blocks_recursive(PAGE_ID)
        print(f"Found {len(blocks)} blocks")
        
        # Parse to text
        text_content = fetcher.parse_blocks_to_text(blocks)
        
        # Extract tables
        tables = fetcher.extract_table_data(blocks)
        print(f"Found {len(tables)} tables")
        
        # Save raw text content
        output_file = "/Users/mohaned.saleh/prd-ticket-agent/notion_rollout_content.txt"
        with open(output_file, "w") as f:
            f.write(text_content)
        print(f"\nSaved text content to: {output_file}")
        
        # Save tables as JSON for easier processing
        tables_file = "/Users/mohaned.saleh/prd-ticket-agent/notion_rollout_tables.json"
        with open(tables_file, "w") as f:
            json.dump(tables, f, indent=2)
        print(f"Saved tables to: {tables_file}")
        
        # Also save full blocks for debugging
        blocks_file = "/Users/mohaned.saleh/prd-ticket-agent/notion_rollout_blocks.json"
        with open(blocks_file, "w") as f:
            json.dump(blocks, f, indent=2, default=str)
        print(f"Saved raw blocks to: {blocks_file}")
        
        print("\n" + "=" * 60)
        print("CONTENT PREVIEW")
        print("=" * 60)
        print(text_content[:3000])
        if len(text_content) > 3000:
            print("\n... [truncated] ...")
        
        return blocks, tables, text_content
        
    except httpx.HTTPStatusError as e:
        print(f"\nError accessing Notion API: {e}")
        if e.response.status_code == 401:
            print("→ Invalid API key. Please check your Notion integration.")
        elif e.response.status_code == 404:
            print("→ Page not found. Make sure the integration has access to this page.")
            print("→ Go to the Notion page → ⋯ → Add connections → Select your integration")
        else:
            print(f"→ HTTP {e.response.status_code}: {e.response.text}")
        return None, None, None


if __name__ == "__main__":
    asyncio.run(fetch_and_save())








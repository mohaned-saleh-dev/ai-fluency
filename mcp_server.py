#!/usr/bin/env python3
"""
MCP Server for PRD and Ticket Writing Agent.
This allows the agent to be accessed via Model Context Protocol.

This is a simplified MCP server that works with Python 3.9+ and doesn't require
the official MCP SDK. It implements the MCP protocol over stdio.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from prd_ticket_agent import PRDTicketAgent, AgentContext
from prd_ticket_agent.config import load_context_from_env

# Initialize agent (will be loaded when needed)
agent = None
context = None


def get_agent():
    """Get or initialize the agent."""
    global agent, context
    if agent is None:
        context = load_context_from_env()
        agent = PRDTicketAgent(context)
    return agent


async def handle_request(request):
    """Handle an MCP request."""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "prd-ticket-agent",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "create_prd",
                            "description": "Create a Product Requirements Document (PRD) based on a project description. The agent will gather context from Notion (squad priorities, existing PRDs, and tickets) and generate a comprehensive PRD following your team's format and style guide.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "project_description": {
                                        "type": "string",
                                        "description": "Description of the project or feature for which to create a PRD"
                                    },
                                    "additional_context": {
                                        "type": "object",
                                        "description": "Optional additional context or requirements",
                                        "additionalProperties": True
                                    }
                                },
                                "required": ["project_description"]
                            }
                        },
                        {
                            "name": "create_ticket",
                            "description": "Create a Jira ticket linked to a PRD. The ticket will be generated based on the PRD content and will follow your team's ticket format and style.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prd_id": {
                                        "type": "string",
                                        "description": "Notion page ID of the PRD (if the PRD exists in Notion)"
                                    },
                                    "prd_content": {
                                        "type": "object",
                                        "description": "PRD content as a dictionary (if PRD is not yet in Notion)"
                                    },
                                    "ticket_description": {
                                        "type": "string",
                                        "description": "Description of the specific ticket to create"
                                    },
                                    "project_key": {
                                        "type": "string",
                                        "description": "Jira project key (e.g., 'PROJ', 'ENG', etc.)"
                                    }
                                },
                                "required": ["project_key"]
                            }
                        },
                        {
                            "name": "get_notion_context",
                            "description": "Retrieve context from Notion including squad priorities, existing PRDs, and tickets. Useful for understanding the current state before creating new PRDs or tickets.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            agent = get_agent()
            
            if tool_name == "create_prd":
                project_description = arguments.get("project_description")
                additional_context = arguments.get("additional_context", {})
                
                if not project_description:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32602,
                            "message": "project_description is required"
                        }
                    }
                
                result = await agent.create_prd(
                    project_description=project_description,
                    additional_context=additional_context
                )
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }
            
            elif tool_name == "create_ticket":
                prd_id = arguments.get("prd_id")
                prd_content = arguments.get("prd_content")
                ticket_description = arguments.get("ticket_description")
                project_key = arguments.get("project_key")
                
                if not project_key:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32602,
                            "message": "project_key is required"
                        }
                    }
                
                result = await agent.create_ticket(
                    prd_id=prd_id,
                    prd_content=prd_content,
                    ticket_description=ticket_description,
                    project_key=project_key
                )
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }
            
            elif tool_name == "get_notion_context":
                context_data = await agent.get_context_from_notion()
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(context_data, indent=2)
                            }
                        ]
                    }
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": str(e),
                "data": {"type": type(e).__name__}
            }
        }


async def main():
    """Main entry point for the MCP server."""
    # Read from stdin, write to stdout
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            request = json.loads(line)
            response = await handle_request(request)
            
            if response:
                print(json.dumps(response), flush=True)
        
        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    asyncio.run(main())


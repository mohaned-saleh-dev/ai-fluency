"""
PRD and Jira Ticket Writing Agent

A focused agent for creating Product Requirements Documents (PRDs) and Jira tickets.
"""

from .agent import PRDTicketAgent, AgentContext, TaskType
from .config import load_context_from_env, load_context_from_file

__version__ = "0.1.0"
__all__ = [
    'PRDTicketAgent',
    'AgentContext',
    'TaskType',
    'load_context_from_env',
    'load_context_from_file'
]



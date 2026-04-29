"""
Jira Ticket Generator module.
Creates Jira tickets linked to PRDs.
"""

from typing import Dict, List, Optional, Any
from .prompts import TICKET_PROMPT_TEMPLATE
from .style_guide import apply_style_guide


class TicketGenerator:
    """Generates Jira tickets based on PRD context."""
    
    def __init__(self, notion_client, jira_client, context):
        self.notion_client = notion_client
        self.jira_client = jira_client
        self.context = context
        self.gemini_client = None
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini client if API key is provided."""
        if self.context.gemini_api_key:
            from .integrations.gemini_client import GeminiClient
            self.gemini_client = GeminiClient(
                api_key=self.context.gemini_api_key,
                model_name=self.context.gemini_model_name
            )
    
    async def generate(
        self,
        prd_id: Optional[str] = None,
        prd_content: Optional[Dict[str, Any]] = None,
        ticket_description: Optional[str] = None,
        project_key: str = None
    ) -> Dict[str, Any]:
        """
        Generate a Jira ticket.
        
        Args:
            prd_id: ID of the PRD in Notion
            prd_content: PRD content dictionary
            ticket_description: Description of the specific ticket
            project_key: Jira project key
            
        Returns:
            Ticket content as dictionary
        """
        # Get PRD content if not provided
        if prd_id and not prd_content:
            prd_content = await self._get_prd_from_notion(prd_id)
        
        if not prd_content:
            raise ValueError("PRD content is required to create a ticket")
        
        # Gather context from existing tickets
        existing_tickets_context = {}
        if self.notion_client and self.context.notion_all_tickets_page_id:
            existing_tickets_context = await self._gather_tickets_context()
        
        # Gather context from Jira
        jira_context = {}
        if self.jira_client:
            jira_context = await self._gather_jira_context(prd_content, ticket_description)
        
        # Build the prompt
        prompt = self._build_prompt(
            prd_content=prd_content,
            ticket_description=ticket_description,
            existing_tickets_context=existing_tickets_context,
            jira_context=jira_context
        )
        
        # Generate ticket content using Gemini
        ticket_content = await self._generate_ticket_structure(prompt)
        
        # Apply style guide
        ticket_content = apply_style_guide(ticket_content)
        
        # Create ticket in Jira if client is available
        jira_issue = None
        if self.jira_client and project_key:
            jira_issue = await self._create_jira_issue(
                ticket_content=ticket_content,
                project_key=project_key
            )
        
        return {
            "content": ticket_content,
            "jira_issue": jira_issue,
            "metadata": {
                "prd_id": prd_id,
                "references_used": self._get_references_used(prd_content, existing_tickets_context, jira_context)
            }
        }
    
    async def _get_prd_from_notion(self, prd_id: str) -> Dict[str, Any]:
        """Retrieve PRD content from Notion."""
        if not self.notion_client:
            return {}
        
        try:
            page_data = await self.notion_client.get_page_content(prd_id)
            # Extract and structure the PRD content
            # This would parse the Notion blocks into the PRD structure
            return self._parse_notion_prd(page_data)
        except Exception as e:
            print(f"Error fetching PRD from Notion: {e}")
            return {}
    
    def _parse_notion_prd(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Notion page data into PRD structure."""
        blocks = page_data.get("blocks", [])
        text_content = self.notion_client.extract_text_from_blocks(blocks)
        
        # Simple parsing - in production, you'd want more robust parsing
        prd_content = {
            "introduction": "",
            "problem_statement": "",
            "goals": "",
            "success_metrics": "",
            "user_personas": "",
            "solution": "",
            "solution_design": "",
            "inclusions_and_exclusions": "",
            "rollout_plan": ""
        }
        
        # Extract sections from text (simplified)
        sections = text_content.split("##")
        for section in sections:
            if "Introduction" in section or "📌" in section:
                prd_content["introduction"] = section
            elif "Problem Statement" in section or "❗" in section:
                prd_content["problem_statement"] = section
            elif "Goals" in section or "🎯" in section:
                prd_content["goals"] = section
            # ... similar for other sections
        
        return prd_content
    
    async def _gather_tickets_context(self) -> Dict[str, Any]:
        """Gather context from existing tickets."""
        try:
            tickets = await self.notion_client.get_database_entries(
                self.context.notion_all_tickets_page_id,
                max_results=2000
            )
            return {"tickets": tickets, "count": len(tickets)}
        except Exception as e:
            print(f"Error fetching tickets context: {e}")
            return {}
    
    async def _gather_jira_context(
        self,
        prd_content: Dict[str, Any],
        ticket_description: Optional[str]
    ) -> Dict[str, Any]:
        """Gather context from Jira issues."""
        if not self.jira_client:
            return {}
        
        context = {}
        
        try:
            # Extract keywords from PRD and ticket description
            search_text = ""
            if prd_content:
                # Combine PRD sections for search
                search_text = " ".join([
                    str(v) for v in prd_content.values()
                    if isinstance(v, str) and v
                ])
            
            if ticket_description:
                search_text += " " + ticket_description
            
            if search_text:
                # Search for related issues
                related_issues = await self.jira_client.search_related_issues(
                    topic=search_text,
                    max_results=10
                )
                
                if related_issues:
                    context['related_issues'] = related_issues
                    context['related_issues_context'] = self.jira_client.extract_issue_context(related_issues)
            
            # Get similar tickets (same project if available)
            # This helps with consistency
            recent_issues = await self.jira_client.get_recent_issues(
                days=60,
                max_results=15
            )
            
            if recent_issues:
                context['recent_issues'] = recent_issues
                context['recent_issues_context'] = self.jira_client.extract_issue_context(recent_issues)
            
        except Exception as e:
            print(f"Error fetching Jira context: {e}")
        
        return context
    
    def _build_prompt(
        self,
        prd_content: Dict[str, Any],
        ticket_description: Optional[str],
        existing_tickets_context: Dict[str, Any],
        jira_context: Dict[str, Any]
    ) -> str:
        """Build the prompt for ticket generation."""
        prompt_parts = [TICKET_PROMPT_TEMPLATE]
        
        # Add PRD context
        prompt_parts.append("\n## PRD Context")
        prompt_parts.append(str(prd_content))
        
        # Add ticket description if provided
        if ticket_description:
            prompt_parts.append(f"\n## Ticket Description\n{ticket_description}")
        
        # Add existing tickets context
        if existing_tickets_context.get('tickets'):
            prompt_parts.append(f"\n## Reference: All Tickets ({existing_tickets_context.get('count', 0)} tickets)")
            prompt_parts.append("Review existing tickets for terminology, technical systems, and writing style consistency.")
        
        # Add Jira context
        if jira_context.get('related_issues_context'):
            prompt_parts.append("\n## Related Jira Issues")
            prompt_parts.append("The following related Jira issues provide context on:")
            prompt_parts.append("- Similar implementations")
            prompt_parts.append("- Technical patterns and approaches")
            prompt_parts.append("- Dependencies and related work")
            prompt_parts.append("- Naming conventions and terminology")
            prompt_parts.append(jira_context['related_issues_context'])
        
        if jira_context.get('recent_issues_context'):
            prompt_parts.append("\n## Recent Jira Issues (for consistency)")
            prompt_parts.append("Recent tickets for style and format consistency:")
            prompt_parts.append(jira_context['recent_issues_context'])
        
        return "\n".join(prompt_parts)
    
    async def _generate_ticket_structure(self, prompt: str) -> Dict[str, Any]:
        """
        Generate ticket structure using Gemini LLM.
        
        Args:
            prompt: Full prompt for ticket generation
            
        Returns:
            Ticket content dictionary
        """
        if not self.gemini_client:
            # Fallback to template if Gemini is not configured
            print("Warning: Gemini API key not configured. Returning template structure.")
            return {
                "user_story": "",
                "acceptance_criteria": [],
                "description": ""
            }
        
        # Enhanced prompt with JSON format instruction
        enhanced_prompt = f"""{prompt}

Please generate a Jira ticket with the following structure. Return the response as a JSON object with these keys:
- user_story: A clear user story in the format "As a [user], I want [goal] so that [benefit]"
- acceptance_criteria: An array of acceptance criteria (list of strings)
- description: A detailed description of the ticket

Follow the writing style guide: use plain language, be concise, avoid AI clichés, and match the terminology from existing tickets."""
        
        try:
            # Generate text response
            response_text = await self.gemini_client.generate_text(
                prompt=enhanced_prompt,
                temperature=0.7,
                response_format="json"
            )
            
            import json
            ticket_content = json.loads(response_text)
            
            # Ensure all keys are present and correct format
            if "user_story" not in ticket_content:
                ticket_content["user_story"] = ""
            if "acceptance_criteria" not in ticket_content:
                ticket_content["acceptance_criteria"] = []
            elif not isinstance(ticket_content["acceptance_criteria"], list):
                # Convert to list if it's a string
                if isinstance(ticket_content["acceptance_criteria"], str):
                    ticket_content["acceptance_criteria"] = [
                        item.strip() 
                        for item in ticket_content["acceptance_criteria"].split("\n") 
                        if item.strip()
                    ]
            if "description" not in ticket_content:
                ticket_content["description"] = ""
            
            return ticket_content
            
        except Exception as e:
            print(f"Error generating ticket with Gemini: {e}")
            # Fallback: try to parse the response differently
            try:
                # Try generating without JSON format constraint
                response_text = await self.gemini_client.generate_text(
                    prompt=enhanced_prompt,
                    temperature=0.7
                )
                
                # Try to extract structured data from text
                ticket_content = self._parse_ticket_from_text(response_text)
                return ticket_content
            except Exception as e2:
                print(f"Error parsing Gemini response: {e2}")
                # Return empty template as last resort
                return {
                    "user_story": "",
                    "acceptance_criteria": [],
                    "description": ""
                }
    
    def _parse_ticket_from_text(self, text: str) -> Dict[str, Any]:
        """Parse ticket content from unstructured text."""
        import re
        
        ticket_content = {
            "user_story": "",
            "acceptance_criteria": [],
            "description": ""
        }
        
        # Try to find user story
        user_story_match = re.search(
            r'(?:user story|user_story)[:]\s*(.+?)(?=\n(?:acceptance|description)|\Z)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        if user_story_match:
            ticket_content["user_story"] = user_story_match.group(1).strip()
        
        # Try to find acceptance criteria
        ac_match = re.search(
            r'(?:acceptance criteria|acceptance_criteria)[:]\s*(.+?)(?=\n(?:description|\Z))',
            text,
            re.IGNORECASE | re.DOTALL
        )
        if ac_match:
            ac_text = ac_match.group(1)
            # Split by lines and clean up
            criteria = [
                item.strip().lstrip("- ").lstrip("* ")
                for item in ac_text.split("\n")
                if item.strip()
            ]
            ticket_content["acceptance_criteria"] = criteria
        
        # Try to find description
        desc_match = re.search(
            r'(?:description)[:]\s*(.+?)(?=\Z)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        if desc_match:
            ticket_content["description"] = desc_match.group(1).strip()
        
        return ticket_content
    
    async def _create_jira_issue(
        self,
        ticket_content: Dict[str, Any],
        project_key: str
    ) -> Optional[Dict[str, Any]]:
        """Create the ticket in Jira."""
        if not self.jira_client:
            return None
        
        # Format user story and acceptance criteria
        user_story = ticket_content.get("user_story", "")
        acceptance_criteria = ticket_content.get("acceptance_criteria", [])
        
        # Build description
        description_parts = [f"**User Story:**\n{user_story}"]
        
        if acceptance_criteria:
            description_parts.append("\n**Acceptance Criteria:**")
            for ac in acceptance_criteria:
                description_parts.append(f"- {ac}")
        
        description_parts.append(f"\n**Description:**\n{ticket_content.get('description', '')}")
        
        description = "\n".join(description_parts)
        
        # Create issue
        try:
            issue = await self.jira_client.create_issue(
                project_key=project_key,
                summary=user_story.split('\n')[0] if user_story else "New Ticket",
                description=description,
                issue_type="Story"
            )
            return issue
        except Exception as e:
            print(f"Error creating Jira issue: {e}")
            return None
    
    def _get_references_used(
        self,
        prd_content: Dict[str, Any],
        existing_tickets_context: Dict[str, Any],
        jira_context: Dict[str, Any] = None
    ) -> List[str]:
        """Get list of references used in ticket generation."""
        references = []
        
        references.append("PRD (linked to this ticket)")
        
        if existing_tickets_context.get('tickets'):
            references.append(
                f"All Tickets document ({existing_tickets_context.get('count', 0)} tickets reviewed for consistency)"
            )
        
        if jira_context:
            if jira_context.get('related_issues'):
                references.append(f"Jira: {len(jira_context['related_issues'])} related issues")
            if jira_context.get('recent_issues'):
                references.append(f"Jira: {len(jira_context['recent_issues'])} recent issues for context")
        
        return references


"""
PRD Generator module.
Creates PRDs following the specified format and style guide.
"""

from typing import Dict, List, Optional, Any
from .prompts import PRD_PROMPT_TEMPLATE
from .style_guide import apply_style_guide


class PRDGenerator:
    """Generates PRDs based on context and requirements."""
    
    def __init__(self, notion_client, context, jira_client=None):
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
        project_description: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a PRD.
        
        Args:
            project_description: Description of the project/feature
            additional_context: Additional context from user
            
        Returns:
            PRD content as dictionary
        """
        # Gather context from Notion
        notion_context = {}
        if self.notion_client:
            notion_context = await self._gather_notion_context()
        
        # Gather context from Jira
        jira_context = {}
        if self.jira_client:
            jira_context = await self._gather_jira_context(project_description)
        
        # Check if this is AI Chatbot work
        ai_chatbot_requirements = None
        if self._is_ai_chatbot_work(project_description):
            ai_chatbot_requirements = await self._load_ai_chatbot_requirements()
        
        # Build the prompt
        prompt = self._build_prompt(
            project_description=project_description,
            notion_context=notion_context,
            jira_context=jira_context,
            ai_chatbot_requirements=ai_chatbot_requirements,
            additional_context=additional_context or {}
        )
        
        # Generate PRD using Gemini LLM
        prd_content = await self._generate_prd_structure(prompt)
        
        # Apply style guide
        prd_content = apply_style_guide(prd_content)
        
        return {
            "content": prd_content,
            "metadata": {
                "project_description": project_description,
                "references_used": self._get_references_used(notion_context, jira_context)
            }
        }
    
    async def _gather_notion_context(self) -> Dict[str, Any]:
        """Gather context from Notion workspace - scans entire space for all documents."""
        context = {}
        
        if not self.notion_client:
            return context
        
        try:
            print("🔍 Scanning Notion workspace for context...")
            
            # Get workspace/page ID from context (defaults to Agent space)
            workspace_id = self.context.notion_workspace_id or "13662429127880a291deebd5d0fdb130"
            
            # Get all pages from the workspace
            # First, try to get the root page and its children
            try:
                # Get the root page content
                root_page = await self.notion_client.get_page_content(workspace_id)
                context['root_page'] = root_page
                
                # Extract knowledge base from entire workspace
                print("  📚 Extracting knowledge from all workspace pages...")
                knowledge_base = await self.notion_client.extract_knowledge_base(
                    max_pages=200  # Get up to 200 pages from the workspace
                )
                
                if knowledge_base:
                    context['workspace_knowledge'] = knowledge_base
                    print(f"  ✅ Extracted knowledge from workspace ({len(knowledge_base)} characters)")
                
                # Also search for specific document types
                print("  🔎 Searching for OKRs, projects, and related documents...")
                
                # Search for OKRs
                okr_results = await self.notion_client.search_workspace(
                    query="OKR",
                    max_results=20,
                    filter_type="page"
                )
                if okr_results:
                    context['okrs'] = []
                    for okr in okr_results[:10]:  # Limit to top 10
                        try:
                            okr_content = await self.notion_client.get_page_content(okr['id'])
                            context['okrs'].append(okr_content)
                        except:
                            continue
                    print(f"  ✅ Found {len(context['okrs'])} OKR documents")
                
                # Search for projects
                project_results = await self.notion_client.search_workspace(
                    query="project",
                    max_results=20,
                    filter_type="page"
                )
                if project_results:
                    context['projects'] = []
                    for project in project_results[:10]:  # Limit to top 10
                        try:
                            project_content = await self.notion_client.get_page_content(project['id'])
                            context['projects'].append(project_content)
                        except:
                            continue
                    print(f"  ✅ Found {len(context['projects'])} project documents")
                
                # Search for PRDs
                prd_results = await self.notion_client.search_workspace(
                    query="PRD",
                    max_results=20,
                    filter_type="page"
                )
                if prd_results:
                    context['existing_prds'] = []
                    for prd in prd_results[:10]:  # Limit to top 10
                        try:
                            prd_content = await self.notion_client.get_page_content(prd['id'])
                            context['existing_prds'].append(prd_content)
                        except:
                            continue
                    print(f"  ✅ Found {len(context['existing_prds'])} existing PRD documents")
                
            except Exception as e:
                print(f"  ⚠️  Error accessing workspace: {e}")
                # Fallback: try to search entire workspace
                try:
                    all_pages = await self.notion_client.get_all_pages_from_space(max_results=100)
                    if all_pages:
                        context['workspace_pages'] = all_pages
                        print(f"  ✅ Found {len(all_pages)} pages in workspace")
                except Exception as e2:
                    print(f"  ⚠️  Error searching workspace: {e2}")
        
        except Exception as e:
            print(f"Error gathering Notion context: {e}")
        
        return context
    
    async def _gather_jira_context(self, project_description: str) -> Dict[str, Any]:
        """Gather comprehensive context from Jira - scans all relevant issues."""
        if not self.jira_client:
            return {}
        
        context = {}
        
        try:
            print("🔍 Scanning Jira for context...")
            
            # 1. Search for related issues based on the project description
            print("  🔎 Searching for related issues...")
            related_issues = await self.jira_client.search_related_issues(
                topic=project_description,
                max_results=20
            )
            
            if related_issues:
                context['related_issues'] = related_issues
                context['related_issues_context'] = self.jira_client.extract_issue_context(related_issues)
                print(f"  ✅ Found {len(related_issues)} related issues")
            
            # 2. Get recent issues for general context (last 90 days)
            print("  📅 Fetching recent issues...")
            recent_issues = await self.jira_client.get_recent_issues(
                days=90,
                max_results=50
            )
            
            if recent_issues:
                context['recent_issues'] = recent_issues
                context['recent_issues_context'] = self.jira_client.extract_issue_context(recent_issues)
                print(f"  ✅ Found {len(recent_issues)} recent issues")
            
            # 3. Get all issues from key projects (if project keys are configured)
            # This gives comprehensive context from active projects
            print("  📊 Fetching issues from key projects...")
            try:
                # Try to get issues from common project patterns
                # You can configure specific project keys if needed
                all_recent_issues = await self.jira_client.get_recent_issues(
                    days=180,  # Last 6 months
                    max_results=100
                )
                
                if all_recent_issues:
                    context['project_issues'] = all_recent_issues
                    context['project_issues_context'] = self.jira_client.extract_issue_context(all_recent_issues[:30])  # Top 30 for context
                    print(f"  ✅ Found {len(all_recent_issues)} issues from projects")
            except Exception as e:
                print(f"  ⚠️  Could not fetch project issues: {e}")
            
            # 4. Extract common patterns and terminology
            if context.get('recent_issues') or context.get('related_issues'):
                all_issues = (context.get('recent_issues', []) + 
                             context.get('related_issues', []) + 
                             context.get('project_issues', []))
                
                if all_issues:
                    # Extract common terminology, system names, patterns
                    context['jira_knowledge'] = self._extract_jira_knowledge(all_issues)
                    print(f"  ✅ Extracted knowledge from {len(all_issues)} total issues")
            
        except Exception as e:
            print(f"  ⚠️  Error fetching Jira context: {e}")
            # Don't fail completely - continue without Jira context
        
        return context
    
    def _extract_jira_knowledge(self, issues: List[Dict[str, Any]]) -> str:
        """Extract common patterns, terminology, and knowledge from Jira issues."""
        knowledge_parts = []
        
        # Collect summaries and descriptions
        summaries = []
        descriptions = []
        components = set()
        labels = set()
        
        for issue in issues[:50]:  # Limit to top 50
            fields = issue.get("fields", {})
            summary = fields.get("summary", "")
            description = fields.get("description", "")
            issue_type = fields.get("issuetype", {}).get("name", "")
            
            if summary:
                summaries.append(f"{issue.get('key', '')} ({issue_type}): {summary}")
            
            if description:
                # Extract text from description (handle ADF format)
                if isinstance(description, dict) and self.jira_client:
                    desc_text = self.jira_client._extract_text_from_adf(description)
                else:
                    desc_text = str(description)
                if desc_text and len(desc_text) > 20:
                    descriptions.append(desc_text[:200])  # Truncate
            
            # Collect components and labels
            issue_components = fields.get("components", [])
            for comp in issue_components:
                components.add(comp.get("name", ""))
            
            issue_labels = fields.get("labels", [])
            labels.update(issue_labels)
        
        knowledge_parts.append("## Recent Jira Issues Summary")
        knowledge_parts.append(f"Found {len(issues)} issues for context")
        
        if summaries:
            knowledge_parts.append("\n### Issue Summaries (for terminology and patterns):")
            knowledge_parts.extend(summaries[:20])  # Top 20 summaries
        
        if components:
            knowledge_parts.append(f"\n### Technical Components in Use:")
            knowledge_parts.append(", ".join(sorted(components)[:20]))
        
        if labels:
            knowledge_parts.append(f"\n### Common Labels:")
            knowledge_parts.append(", ".join(sorted(list(labels))[:20]))
        
        if descriptions:
            knowledge_parts.append("\n### Sample Descriptions (for writing style):")
            knowledge_parts.extend(descriptions[:10])  # Top 10 descriptions
        
        return "\n".join(knowledge_parts)
    
    def _is_ai_chatbot_work(self, description: str) -> bool:
        """Check if the work involves AI Chatbot."""
        keywords = ['ai chatbot', 'chatbot', 'ai chat', 'conversational ai']
        description_lower = description.lower()
        return any(keyword in description_lower for keyword in keywords)
    
    async def _load_ai_chatbot_requirements(self) -> Optional[Dict[str, Any]]:
        """Load AI Chatbot Functional Requirements CSV."""
        if not self.context.ai_chatbot_csv_path:
            return None
        
        import csv
        import os
        
        if not os.path.exists(self.context.ai_chatbot_csv_path):
            return None
        
        requirements = []
        with open(self.context.ai_chatbot_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            requirements = list(reader)
        
        return {"requirements": requirements}
    
    def _build_prompt(
        self,
        project_description: str,
        notion_context: Dict[str, Any],
        jira_context: Dict[str, Any],
        ai_chatbot_requirements: Optional[Dict[str, Any]],
        additional_context: Dict[str, Any]
    ) -> str:
        """Build the prompt for PRD generation."""
        prompt_parts = [PRD_PROMPT_TEMPLATE]
        
        # Add project description
        prompt_parts.append(f"\n## Project Description\n{project_description}")
        
        # Add workspace knowledge base (all documents from the space)
        if notion_context.get('workspace_knowledge'):
            prompt_parts.append("\n## Workspace Knowledge Base")
            prompt_parts.append("The following is knowledge extracted from your entire Notion workspace:")
            prompt_parts.append("This includes OKRs, projects, PRDs, and all other documents.")
            prompt_parts.append("Use this for context on:")
            prompt_parts.append("- Strategic goals and OKRs")
            prompt_parts.append("- Existing projects and initiatives")
            prompt_parts.append("- Technical systems and architecture")
            prompt_parts.append("- Team priorities and focus areas")
            prompt_parts.append("- Terminology and conventions")
            # Include a substantial portion of the knowledge base (limit to avoid token limits)
            knowledge_text = notion_context['workspace_knowledge']
            if len(knowledge_text) > 10000:
                knowledge_text = knowledge_text[:10000] + "\n\n[Additional content truncated for length...]"
            prompt_parts.append(f"\n{knowledge_text}")
        
        # Add OKRs context
        if notion_context.get('okrs'):
            prompt_parts.append(f"\n## OKRs Context ({len(notion_context['okrs'])} documents)")
            prompt_parts.append("Review these OKR documents to ensure alignment with objectives and key results:")
            for i, okr in enumerate(notion_context['okrs'][:5], 1):  # Top 5 OKRs
                okr_text = self.notion_client.extract_text_from_blocks(okr.get('blocks', []))
                if okr_text:
                    prompt_parts.append(f"\n### OKR Document {i}\n{okr_text[:500]}...")  # Truncate for length
        
        # Add projects context
        if notion_context.get('projects'):
            prompt_parts.append(f"\n## Projects Context ({len(notion_context['projects'])} documents)")
            prompt_parts.append("Review these project documents for related work and dependencies:")
            for i, project in enumerate(notion_context['projects'][:5], 1):  # Top 5 projects
                project_text = self.notion_client.extract_text_from_blocks(project.get('blocks', []))
                if project_text:
                    prompt_parts.append(f"\n### Project Document {i}\n{project_text[:500]}...")  # Truncate for length
        
        # Add existing PRDs for format reference
        if notion_context.get('existing_prds'):
            prompt_parts.append(f"\n## Reference: Existing PRDs ({len(notion_context['existing_prds'])} documents)")
            prompt_parts.append("Review these PRDs to ensure consistency in structure, tone, and depth:")
            for i, prd in enumerate(notion_context['existing_prds'][:3], 1):  # Top 3 PRDs
                prd_text = self.notion_client.extract_text_from_blocks(prd.get('blocks', []))
                if prd_text:
                    prompt_parts.append(f"\n### PRD Example {i}\n{prd_text[:1000]}...")  # Truncate for length
        
        # Add Jira context
        if jira_context.get('jira_knowledge'):
            prompt_parts.append("\n## Jira Knowledge Base")
            prompt_parts.append("The following is knowledge extracted from Jira issues:")
            prompt_parts.append("- Technical components and systems in use")
            prompt_parts.append("- Common terminology and naming conventions")
            prompt_parts.append("- Writing patterns and issue formats")
            prompt_parts.append("- Recent work and patterns")
            prompt_parts.append(jira_context['jira_knowledge'])
        
        if jira_context.get('related_issues_context'):
            prompt_parts.append("\n## Related Jira Issues")
            prompt_parts.append("The following Jira issues are directly related to this project:")
            prompt_parts.append("- Similar implementations")
            prompt_parts.append("- Dependencies and related work")
            prompt_parts.append("- Technical patterns and approaches")
            prompt_parts.append(jira_context['related_issues_context'])
        
        if jira_context.get('recent_issues_context'):
            prompt_parts.append("\n## Recent Jira Issues (for consistency)")
            prompt_parts.append("Recent work in Jira for style and format consistency:")
            prompt_parts.append(jira_context['recent_issues_context'])
        
        # Add AI Chatbot requirements if applicable
        if ai_chatbot_requirements:
            prompt_parts.append("\n## AI Chatbot Functional Requirements")
            prompt_parts.append("Ensure alignment with AI Chatbot requirements.")
        
        # Add additional context
        if additional_context:
            prompt_parts.append("\n## Additional Context")
            prompt_parts.append(str(additional_context))
        
        return "\n".join(prompt_parts)
    
    async def _generate_prd_structure(self, prompt: str) -> Dict[str, Any]:
        """
        Generate PRD structure using Gemini LLM.
        
        Args:
            prompt: Full prompt for PRD generation
            
        Returns:
            PRD content dictionary
        """
        if not self.gemini_client:
            # Fallback to template if Gemini is not configured
            print("Warning: Gemini API key not configured. Returning template structure.")
            return {
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
        
        # Define the expected output schema
        output_schema = {
            "introduction": "string",
            "problem_statement": "string",
            "goals": "string",
            "success_metrics": "string",
            "user_personas": "string",
            "solution": "string",
            "solution_design": "string",
            "inclusions_and_exclusions": "string",
            "rollout_plan": "string"
        }
        
        # Enhanced prompt with JSON format instruction
        enhanced_prompt = f"""{prompt}

Please generate a comprehensive PRD with all required sections. Return the response as a JSON object with the following keys:
- introduction
- problem_statement
- goals
- success_metrics
- user_personas
- solution
- solution_design
- inclusions_and_exclusions
- rollout_plan

Each section should be well-written, detailed, and follow the writing style guide (plain language, no AI clichés, concise and clear)."""
        
        try:
            # Generate structured output
            prd_content = await self.gemini_client.generate_structured_output(
                prompt=enhanced_prompt,
                output_schema=output_schema,
                temperature=0.7
            )
            
            # Ensure all keys are present
            for key in output_schema.keys():
                if key not in prd_content:
                    prd_content[key] = ""
            
            return prd_content
            
        except Exception as e:
            print(f"Error generating PRD with Gemini: {e}")
            # Fallback to generating text and parsing
            try:
                response_text = await self.gemini_client.generate_text(
                    prompt=enhanced_prompt,
                    temperature=0.7,
                    response_format="json"
                )
                
                import json
                prd_content = json.loads(response_text)
                
                # Ensure all keys are present
                for key in output_schema.keys():
                    if key not in prd_content:
                        prd_content[key] = ""
                
                return prd_content
            except Exception as e2:
                print(f"Error parsing Gemini response: {e2}")
                # Return empty template as last resort
                return {
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
    
    def _get_references_used(self, notion_context: Dict[str, Any], jira_context: Dict[str, Any] = None) -> List[str]:
        """Get list of references used in PRD generation."""
        references = []
        
        if notion_context.get('workspace_knowledge'):
            kb_size = len(notion_context['workspace_knowledge'])
            references.append(f"Notion Workspace: {kb_size} characters of knowledge from entire space")
        
        if notion_context.get('okrs'):
            references.append(f"Notion: {len(notion_context['okrs'])} OKR documents")
        
        if notion_context.get('projects'):
            references.append(f"Notion: {len(notion_context['projects'])} project documents")
        
        if notion_context.get('existing_prds'):
            references.append(f"Notion: {len(notion_context['existing_prds'])} existing PRD documents (for format consistency)")
        
        if jira_context:
            total_issues = (
                len(jira_context.get('related_issues', [])) +
                len(jira_context.get('recent_issues', [])) +
                len(jira_context.get('project_issues', []))
            )
            if total_issues > 0:
                references.append(f"Jira: {total_issues} issues scanned for context")
            if jira_context.get('jira_knowledge'):
                references.append("Jira: Knowledge base extracted (components, terminology, patterns)")
        
        return references
    
    def format_for_notion(self, prd_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Format PRD content as Notion blocks.
        
        Args:
            prd_content: PRD content dictionary
            
        Returns:
            List of Notion block objects
        """
        blocks = []
        
        # Introduction
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": "📌 Introduction"}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": prd_content.get("introduction", "")}]
            }
        })
        
        # Problem Statement
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": "❗ Problem Statement"}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": prd_content.get("problem_statement", "")}]
            }
        })
        
        # Goals
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": "🎯 Goals"}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": prd_content.get("goals", "")}]
            }
        })
        
        # Success Metrics
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": "📊 Success Metrics (must align with CPX 2025)"}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": prd_content.get("success_metrics", "")}]
            }
        })
        
        # User Personas
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": "👤 User Personas"}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": prd_content.get("user_personas", "")}]
            }
        })
        
        # Solution
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": "💡 Solution"}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": prd_content.get("solution", "")}]
            }
        })
        
        # Solution Design
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": "📐 Solution Design"}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": prd_content.get("solution_design", "")}]
            }
        })
        
        # Inclusions and Exclusions
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": "✅ Inclusions and Exclusions"}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": prd_content.get("inclusions_and_exclusions", "")}]
            }
        })
        
        # Roll-out Plan
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": "🚀 Roll-out Plan"}]
            }
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": prd_content.get("rollout_plan", "")}]
            }
        })
        
        return blocks


"""
Google Gemini LLM client for generating PRDs and tickets.
"""

from typing import Dict, List, Optional, Any
import json
import re


class GeminiClient:
    """Client for interacting with Google Gemini API."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-pro"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google AI API key
            model_name: Model name (default: "gemini-pro")
        """
        self.api_key = api_key
        self.model_name = model_name
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Gemini client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model_name)
        except ImportError:
            raise ImportError(
                "google-generativeai package is required. "
                "Install it with: pip install google-generativeai"
            )
    
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None
    ) -> str:
        """
        Generate text using Gemini.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            response_format: Optional format specification (e.g., "json")
            
        Returns:
            Generated text
        """
        import asyncio
        
        if not self._client:
            self._initialize_client()
        
        # Configure generation parameters
        generation_config = {
            "temperature": temperature,
        }
        
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        # Add format instruction if JSON is requested
        if response_format == "json":
            prompt = f"{prompt}\n\nPlease respond with valid JSON only, no additional text."
        
        try:
            # Run the synchronous call in an executor to make it async-friendly
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.generate_content(
                    prompt,
                    generation_config=generation_config
                )
            )
            
            if response and response.text:
                text = response.text.strip()
                
                # If JSON format was requested, try to extract JSON
                if response_format == "json":
                    text = self._extract_json(text)
                
                return text
            else:
                raise ValueError("Empty response from Gemini")
                
        except Exception as e:
            raise RuntimeError(f"Error generating text with Gemini: {e}")
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text response."""
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return text
    
    async def generate_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate structured output matching a schema.
        
        Args:
            prompt: Input prompt
            output_schema: Dictionary describing the expected output structure
            temperature: Sampling temperature
            
        Returns:
            Dictionary matching the schema
        """
        # Build schema description
        schema_description = self._format_schema(output_schema)
        
        enhanced_prompt = f"""{prompt}

Please respond with a JSON object matching this structure:
{schema_description}

Return only valid JSON, no additional text."""
        
        response_text = await self.generate_text(
            prompt=enhanced_prompt,
            temperature=temperature,
            response_format="json"
        )
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: try to parse as structured text
            return self._parse_structured_text(response_text, output_schema)
    
    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format schema dictionary as a description."""
        description_parts = []
        for key, value_type in schema.items():
            if isinstance(value_type, dict):
                description_parts.append(f"- {key}: object with keys: {', '.join(value_type.keys())}")
            elif isinstance(value_type, list):
                description_parts.append(f"- {key}: list of {value_type[0] if value_type else 'items'}")
            else:
                description_parts.append(f"- {key}: {value_type}")
        return "\n".join(description_parts)
    
    def _parse_structured_text(self, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Parse structured text into dictionary."""
        result = {}
        
        # Simple parsing - look for key-value patterns
        for key in schema.keys():
            # Try to find the key and its value
            pattern = rf"{key}[:]\s*(.+?)(?=\n\w+[:]|\Z)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                result[key] = match.group(1).strip()
            else:
                result[key] = ""
        
        return result


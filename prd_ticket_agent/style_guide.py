"""
Writing style guide enforcement.
Applies the style guide rules to generated content.
"""

from typing import Dict, Any, List
import re


# AI clichés to avoid
AI_CLICHES = [
    r"let's dive (into|deep)",
    r"game-changing",
    r"revolutionary",
    r"transform your life",
    r"unlock the power",
    r"leverage",
    r"harness",
    r"empower",
    r"seamless",
    r"cutting-edge",
    r"next-level",
    r"take it to the next level",
    r"world-class",
    r"industry-leading"
]

# Patterns to simplify
SIMPLIFICATION_PATTERNS = [
    (r"we should look into having a meeting at some point", "we should meet"),
    (r"at some point in time", "when"),
    (r"in order to", "to"),
    (r"due to the fact that", "because"),
    (r"in the event that", "if"),
    (r"with regard to", "about"),
    (r"for the purpose of", "to"),
]


def apply_style_guide(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply style guide rules to content.
    
    Args:
        content: Content dictionary (PRD or ticket)
        
    Returns:
        Content with style guide applied
    """
    if isinstance(content, dict):
        processed = {}
        for key, value in content.items():
            if isinstance(value, str):
                processed[key] = _process_text(value)
            elif isinstance(value, list):
                processed[key] = [_process_text(item) if isinstance(item, str) else item for item in value]
            else:
                processed[key] = value
        return processed
    elif isinstance(content, str):
        return _process_text(content)
    else:
        return content


def _process_text(text: str) -> str:
    """
    Process text according to style guide.
    
    Rules:
    1. Remove AI clichés
    2. Simplify verbose phrases
    3. Ensure natural tone
    4. Keep it concise
    """
    if not text:
        return text
    
    # Remove AI clichés
    for cliche_pattern in AI_CLICHES:
        text = re.sub(cliche_pattern, "", text, flags=re.IGNORECASE)
    
    # Simplify verbose phrases
    for pattern, replacement in SIMPLIFICATION_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def check_style_compliance(text: str) -> List[str]:
    """
    Check if text complies with style guide.
    
    Returns:
        List of style violations found
    """
    violations = []
    
    # Check for AI clichés
    for cliche_pattern in AI_CLICHES:
        if re.search(cliche_pattern, text, re.IGNORECASE):
            violations.append(f"Found AI cliché: {cliche_pattern}")
    
    # Check for verbose phrases
    for pattern, _ in SIMPLIFICATION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(f"Found verbose phrase: {pattern}")
    
    return violations




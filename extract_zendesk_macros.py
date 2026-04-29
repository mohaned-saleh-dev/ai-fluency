#!/usr/bin/env python3
"""
Extract all macros from Zendesk via API and save as CSV.
"""

import os
import csv
import json
import sys
import re
import httpx
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from html import unescape
import argparse

# Load environment variables
load_dotenv()


def get_zendesk_credentials(
    subdomain: Optional[str] = None,
    email: Optional[str] = None,
    api_token: Optional[str] = None
):
    """Get Zendesk credentials from arguments or environment variables."""
    subdomain = subdomain or os.getenv("ZENDESK_SUBDOMAIN")
    email = email or os.getenv("ZENDESK_EMAIL")
    api_token = api_token or os.getenv("ZENDESK_API_TOKEN")
    
    if not subdomain or not email or not api_token:
        raise ValueError(
            "Missing Zendesk credentials. Please provide:\n"
            "  - ZENDESK_SUBDOMAIN (e.g., 'yourcompany' for yourcompany.zendesk.com)\n"
            "  - ZENDESK_EMAIL (your Zendesk email)\n"
            "  - ZENDESK_API_TOKEN (your Zendesk API token)\n"
            "\nYou can:\n"
            "  1. Set environment variables: ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_API_TOKEN\n"
            "  2. Pass as command-line arguments: --subdomain, --email, --api-token\n"
            "\nTo get an API token:\n"
            "  Admin > Apps and integrations > APIs > Zendesk API > Add API token"
        )
    
    return subdomain, email, api_token


def create_zendesk_client(subdomain: str, email: str, api_token: str) -> httpx.Client:
    """Create an authenticated httpx client for Zendesk API."""
    base_url = f"https://{subdomain}.zendesk.com"
    auth = (f"{email}/token", api_token)
    
    client = httpx.Client(
        base_url=base_url,
        auth=auth,
        headers={"Content-Type": "application/json"},
        timeout=30.0
    )
    
    return client


def fetch_all_macros(client: httpx.Client) -> List[Dict[str, Any]]:
    """Fetch all macros from Zendesk API."""
    all_macros = []
    url = "/api/v2/macros.json"
    
    while url:
        try:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            
            macros = data.get("macros", [])
            all_macros.extend(macros)
            
            # Check for pagination
            url = data.get("next_page")
            
            print(f"Fetched {len(macros)} macros (total: {len(all_macros)})...")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Authentication failed. Please check your Zendesk credentials.")
            elif e.response.status_code == 403:
                raise ValueError("Access forbidden. Please check your Zendesk permissions.")
            else:
                raise RuntimeError(f"Error fetching macros: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Error fetching macros: {str(e)}")
    
    return all_macros


def extract_action_types(actions: List[Dict[str, Any]]) -> str:
    """Extract action types from actions list."""
    if not actions:
        return ""
    types = [action.get("field", "") for action in actions]
    return ", ".join(types)


def format_actions(actions: List[Dict[str, Any]]) -> str:
    """Format actions list as JSON string."""
    if not actions:
        return ""
    return json.dumps(actions)


def format_macro_body(macro: Dict[str, Any]) -> str:
    """Extract macro body/description text."""
    # The macro body might be in different fields depending on Zendesk version
    # Try common fields
    body = macro.get("macro_body") or macro.get("body") or macro.get("description") or ""
    return str(body) if body else ""


def extract_text_from_html(html: str) -> str:
    """Extract plain text from HTML, removing tags and decoding entities."""
    if not html:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html)
    # Decode HTML entities
    text = unescape(text)
    # Replace multiple whitespace with single space
    text = ' '.join(text.split())
    return text.strip()


def extract_macro_text_from_actions(actions: List[Dict[str, Any]]) -> str:
    """Extract macro text from comment_value_html in actions."""
    if not actions:
        return ""
    
    for action in actions:
        field = action.get("field", "")
        if "comment_value_html" in field:
            html_value = action.get("value", "")
            if html_value:
                return extract_text_from_html(html_value)
        # Also check for comment_value (plain text)
        elif field == "comment_value":
            value = action.get("value", "")
            if value:
                return extract_text_from_html(value)  # In case it has HTML entities
    
    return ""


def get_base_title(title: str) -> str:
    """Extract base title by removing language prefix and suffix."""
    base = title.strip()
    
    # Remove language prefixes like "Merchant Arabic::" or "Merchant English::"
    if "::" in base:
        base = base.split("::", 1)[-1].strip()
    
    # Remove language suffixes like " [AR]", " [EN]", " [Arabic]", " [English]"
    base = re.sub(r'\s*\[(AR|EN|Arabic|English|ar|en)\]\s*$', '', base, flags=re.IGNORECASE)
    
    # Remove other common language indicators
    base = re.sub(r'\s*\(AR\)\s*$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'\s*\(EN\)\s*$', '', base, flags=re.IGNORECASE)
    
    return base.strip()


def detect_title_language(title: str) -> Optional[str]:
    """Detect if title indicates Arabic or English version."""
    title_lower = title.lower()
    if "arabic" in title_lower or "ar" in title_lower:
        return "ar"
    elif "english" in title_lower or "en" in title_lower:
        return "en"
    return None


def detect_text_language(text: str) -> Optional[str]:
    """Detect language of text content."""
    if not text:
        return None
    # Check for Arabic characters (Unicode range for Arabic)
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    has_arabic = bool(arabic_pattern.search(text))
    # Check for English (basic Latin characters)
    has_english = bool(re.search(r'[a-zA-Z]', text))
    
    if has_arabic and not has_english:
        return "ar"
    elif has_english and not has_arabic:
        return "en"
    elif has_arabic and has_english:
        # If both, check which is more dominant
        arabic_chars = len(arabic_pattern.findall(text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        return "ar" if arabic_chars > english_chars else "en"
    return None


def process_macro(macro: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single macro into the required CSV format."""
    actions = macro.get("actions", [])
    title = macro.get("title", "")
    
    # Extract macro text from actions
    macro_text = extract_macro_text_from_actions(actions)
    
    # Determine language from title or text content
    title_lang = detect_title_language(title)
    text_lang = detect_text_language(macro_text) if macro_text else None
    
    # Use title language if available, otherwise use text language
    detected_lang = title_lang or text_lang
    
    # Initialize both language columns
    macro_text_arabic = ""
    macro_text_english = ""
    
    # Assign text to appropriate column based on detected language
    if detected_lang == "ar":
        macro_text_arabic = macro_text
    elif detected_lang == "en":
        macro_text_english = macro_text
    elif macro_text:
        # If language unclear but text exists, try to detect from content
        content_lang = detect_text_language(macro_text)
        if content_lang == "ar":
            macro_text_arabic = macro_text
        elif content_lang == "en":
            macro_text_english = macro_text
        else:
            # Default to English if can't determine
            macro_text_english = macro_text
    
    return {
        "action_types": extract_action_types(actions),
        "actions": format_actions(actions),
        "active": macro.get("active", False),
        "created_at": macro.get("created_at", ""),
        "description": macro.get("description", ""),
        "id": macro.get("id", ""),
        "macro_body": format_macro_body(macro),
        "macro_text_arabic": macro_text_arabic,
        "macro_text_english": macro_text_english,
        "position": macro.get("position", ""),
        "restriction_id": macro.get("restriction", {}).get("id", "") if isinstance(macro.get("restriction"), dict) else "",
        "restriction_type": macro.get("restriction", {}).get("type", "") if isinstance(macro.get("restriction"), dict) else "",
        "title": title,
        "updated_at": macro.get("updated_at", "")
    }


def enrich_with_matching_versions(processed_macros: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich macros with matching Arabic/English versions by populating both language columns."""
    # Group macros by base title
    title_groups = {}
    for macro in processed_macros:
        base_title = get_base_title(macro["title"])
        if base_title not in title_groups:
            title_groups[base_title] = []
        title_groups[base_title].append(macro)
    
    # For each macro, find matching versions and populate both columns
    enriched_macros = []
    for macro in processed_macros:
        base_title = get_base_title(macro["title"])
        group = title_groups.get(base_title, [macro])
        
        # Find Arabic and English versions in the group
        arabic_text = macro.get("macro_text_arabic", "")
        english_text = macro.get("macro_text_english", "")
        
        # Look for matching versions
        for other_macro in group:
            if other_macro["id"] == macro["id"]:
                continue  # Skip self
            
            other_arabic = other_macro.get("macro_text_arabic", "")
            other_english = other_macro.get("macro_text_english", "")
            
            # If we found Arabic text in another version, use it
            if other_arabic and not arabic_text:
                arabic_text = other_arabic
            # If we found English text in another version, use it
            if other_english and not english_text:
                english_text = other_english
            
            # Also check the detected language from title
            other_title_lang = detect_title_language(other_macro["title"])
            other_macro_text = other_arabic or other_english
            if other_macro_text:
                if other_title_lang == "ar" and not arabic_text:
                    arabic_text = other_macro_text
                elif other_title_lang == "en" and not english_text:
                    english_text = other_macro_text
        
        # Update the macro with both language texts
        enriched = macro.copy()
        enriched["macro_text_arabic"] = arabic_text
        enriched["macro_text_english"] = english_text
        enriched_macros.append(enriched)
    
    return enriched_macros


def save_to_csv(macros: List[Dict[str, Any]], output_path: str = "zendesk_macros.csv"):
    """Save macros to CSV file."""
    if not macros:
        print("No macros found to export.")
        return
    
    # Define column order
    columns = [
        "action_types",
        "actions",
        "active",
        "created_at",
        "description",
        "id",
        "macro_body",
        "macro_text_arabic",
        "macro_text_english",
        "position",
        "restriction_id",
        "restriction_type",
        "title",
        "updated_at"
    ]
    
    # Process macros
    print("📝 Processing macros and extracting text...")
    processed_macros = [process_macro(macro) for macro in macros]
    
    # Enrich with matching Arabic/English versions
    print("🔗 Matching Arabic and English versions...")
    enriched_macros = enrich_with_matching_versions(processed_macros)
    
    # Write to CSV
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(enriched_macros)
    
    print(f"\n✅ Successfully exported {len(enriched_macros)} macros to {output_path}")


def main():
    """Main function to extract and export Zendesk macros."""
    parser = argparse.ArgumentParser(
        description="Extract all macros from Zendesk via API and save as CSV"
    )
    parser.add_argument(
        "--subdomain",
        help="Zendesk subdomain (e.g., 'yourcompany' for yourcompany.zendesk.com)"
    )
    parser.add_argument(
        "--email",
        help="Zendesk email address"
    )
    parser.add_argument(
        "--api-token",
        help="Zendesk API token"
    )
    parser.add_argument(
        "--output",
        default="zendesk_macros.csv",
        help="Output CSV file path (default: zendesk_macros.csv)"
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting Zendesk macro extraction...\n")
    
    try:
        # Get credentials
        subdomain, email, api_token = get_zendesk_credentials(
            subdomain=args.subdomain,
            email=args.email,
            api_token=args.api_token
        )
        print(f"📋 Connecting to Zendesk: {subdomain}.zendesk.com")
        print(f"👤 Using email: {email}\n")
        
        # Create client
        client = create_zendesk_client(subdomain, email, api_token)
        
        # Fetch all macros
        print("📥 Fetching macros from Zendesk API...")
        macros = fetch_all_macros(client)
        
        if not macros:
            print("⚠️  No macros found in your Zendesk instance.")
            return
        
        # Save to CSV
        save_to_csv(macros, args.output)
        
        print(f"\n✨ Done! Macros exported to: {os.path.abspath(args.output)}")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())


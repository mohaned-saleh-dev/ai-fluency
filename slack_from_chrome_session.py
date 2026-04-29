#!/usr/bin/env python3
"""
Extract Slack session from existing Chrome browser and manage threads.
This script connects to your existing Chrome session to access Slack.
"""

import os
import json
import sqlite3
import subprocess
import platform
from pathlib import Path
from datetime import datetime, timedelta
import requests
from typing import List, Dict, Optional

# Chrome cookie database paths
CHROME_COOKIE_PATHS = {
    'darwin': [
        '~/Library/Application Support/Google/Chrome/Default/Cookies',
        '~/Library/Application Support/Google/Chrome/Profile */Cookies',
    ],
    'linux': [
        '~/.config/google-chrome/Default/Cookies',
        '~/.config/google-chrome/Profile */Cookies',
    ],
    'win32': [
        '~/AppData/Local/Google/Chrome/User Data/Default/Cookies',
        '~/AppData/Local/Google/Chrome/User Data/Profile */Cookies',
    ]
}


def get_chrome_cookies(domain='slack.com'):
    """Extract cookies from Chrome's cookie database."""
    system = platform.system().lower()
    cookie_paths = CHROME_COOKIE_PATHS.get(system, [])
    
    cookies = {}
    
    for pattern in cookie_paths:
        expanded = Path(os.path.expanduser(pattern))
        
        # Handle wildcard profiles
        if '*' in str(expanded):
            parent = expanded.parent
            if parent.exists():
                for profile_dir in parent.glob('Profile *'):
                    cookie_file = profile_dir / 'Cookies'
                    if cookie_file.exists():
                        try:
                            profile_cookies = read_chrome_cookies(cookie_file, domain)
                            cookies.update(profile_cookies)
                        except Exception as e:
                            print(f"⚠️  Could not read {cookie_file}: {e}")
        else:
            if expanded.exists():
                try:
                    profile_cookies = read_chrome_cookies(expanded, domain)
                    cookies.update(profile_cookies)
                except Exception as e:
                    print(f"⚠️  Could not read {expanded}: {e}")
    
    return cookies


def read_chrome_cookies(cookie_file: Path, domain: str):
    """Read cookies from Chrome's SQLite database."""
    cookies = {}
    
    # Copy the cookie file to a temp location (Chrome locks it)
    import tempfile
    import shutil
    
    temp_cookie = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_cookie.close()
    
    try:
        shutil.copy2(cookie_file, temp_cookie.name)
        
        conn = sqlite3.connect(temp_cookie.name)
        cursor = conn.cursor()
        
        # Chrome stores cookies with encrypted values, but we can get the names
        cursor.execute("""
            SELECT name, value, host_key, path, expires_utc, is_secure
            FROM cookies
            WHERE host_key LIKE ? OR host_key LIKE ?
        """, (f'%{domain}', f'%.{domain}'))
        
        for row in cursor.fetchall():
            name, value, host_key, path, expires_utc, is_secure = row
            # Chrome encrypts cookie values, so we can't directly use them
            # But we can identify important cookies
            cookies[name] = {
                'value': value,
                'domain': host_key,
                'path': path,
                'expires': expires_utc,
                'secure': bool(is_secure)
            }
        
        conn.close()
    finally:
        os.unlink(temp_cookie.name)
    
    return cookies


def get_slack_workspace_url():
    """Try to get Slack workspace URL from Chrome's local storage or history."""
    # This is a simplified approach - in practice, we'd need to access Chrome's
    # local storage or ask the user for their workspace URL
    return None


def access_slack_via_browser_automation():
    """
    Alternative: Use Selenium or Playwright to connect to existing Chrome instance.
    This requires Chrome to be started with remote debugging enabled.
    """
    print("🔍 Attempting to connect to existing Chrome session...")
    print("\nTo use this method, you need to:")
    print("1. Close Chrome completely")
    print("2. Start Chrome with remote debugging:")
    print("   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
    print("3. Log into Slack in that Chrome instance")
    print("4. Run this script again")
    
    # Check if Chrome is running with remote debugging
    try:
        response = requests.get('http://localhost:9222/json', timeout=2)
        tabs = response.json()
        
        # Find Slack tab
        slack_tab = None
        for tab in tabs:
            if 'slack.com' in tab.get('url', ''):
                slack_tab = tab
                break
        
        if slack_tab:
            print(f"✓ Found Slack tab: {slack_tab['title']}")
            return slack_tab
        else:
            print("⚠️  Chrome remote debugging is enabled but no Slack tab found")
            return None
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Chrome remote debugging not enabled")
        return None
    except Exception as e:
        print(f"⚠️  Error checking Chrome: {e}")
        return None


def get_slack_api_token_from_browser():
    """
    Try to extract Slack API token from browser's localStorage or sessionStorage.
    This requires accessing the browser's JavaScript context.
    """
    print("\n📋 Attempting to extract Slack token from browser session...")
    print("This requires Chrome remote debugging to be enabled.")
    
    tab = access_slack_via_browser_automation()
    if not tab:
        return None
    
    # Use Chrome DevTools Protocol to execute JavaScript in the page
    # This would extract the token from localStorage
    # For now, we'll provide instructions
    print("\nTo extract the token manually:")
    print("1. Open Chrome DevTools (F12)")
    print("2. Go to Application > Local Storage > https://app.slack.com")
    print("3. Look for keys like 'localConfig_v2' or 'token'")
    print("4. Or check Network tab for API requests to see the Authorization header")
    
    return None


def main():
    """Main function to manage Slack threads using existing browser session."""
    print("🚀 Slack Thread Manager - Using Existing Chrome Session")
    print("=" * 80)
    
    # Try to get cookies from Chrome
    print("\n📋 Step 1: Extracting cookies from Chrome...")
    cookies = get_chrome_cookies('slack.com')
    
    if cookies:
        print(f"✓ Found {len(cookies)} cookies for slack.com")
        important_cookies = [name for name in cookies.keys() if any(
            keyword in name.lower() for keyword in ['token', 'session', 'auth', 'x-', 'd-']
        )]
        if important_cookies:
            print(f"  Important cookies found: {', '.join(important_cookies[:5])}")
    else:
        print("⚠️  No cookies found. Make sure Chrome is closed or use remote debugging.")
    
    # Try remote debugging approach
    print("\n📋 Step 2: Checking for Chrome remote debugging...")
    tab = access_slack_via_browser_automation()
    
    if not tab:
        print("\n" + "=" * 80)
        print("ALTERNATIVE APPROACH:")
        print("=" * 80)
        print("\nSince we can't directly access your existing Chrome session,")
        print("here are your options:")
        print("\n1. EASIEST: Get a Slack API token")
        print("   - Go to https://api.slack.com/apps")
        print("   - Create/select an app")
        print("   - Install to workspace")
        print("   - Copy the token")
        print("   - Run: python3 slack_thread_manager.py")
        print("\n2. MANUAL: Use the browser extension")
        print("   - I can open Slack in the browser extension")
        print("   - You log in there")
        print("   - I'll manage threads through that session")
        print("\n3. ADVANCED: Enable Chrome remote debugging")
        print("   - Close Chrome")
        print("   - Start: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
        print("   - Log into Slack")
        print("   - Run this script again")
        
        # Ask if they want to use the browser extension approach
        print("\n" + "=" * 80)
        print("Would you like me to open Slack in the browser extension so you can log in?")
        print("(This will be a separate browser window, but you can log in with JumpCloud)")


if __name__ == "__main__":
    main()













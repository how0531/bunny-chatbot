"""
Extract AlphaMemo cookies from Chrome/Edge browser.

This script will:
1. Find your Chrome/Edge profile
2. Extract cookies for alphamemo.ai
3. Save them to backend/.secrets/alphamemo_cookies.json

Usage:
    python scripts/extract_browser_cookies.py
"""
import json
import os
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SECRETS_DIR = PROJECT_ROOT / 'backend' / '.secrets'
COOKIES_FILE = SECRETS_DIR / 'alphamemo_cookies.json'

# Ensure secrets directory exists
SECRETS_DIR.mkdir(parents=True, exist_ok=True)

def find_chrome_cookies_db():
    """Find Chrome/Edge cookies database."""
    possible_paths = [
        # Chrome
        Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'Network' / 'Cookies',
        # Edge
        Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'Edge' / 'User Data' / 'Default' / 'Network' / 'Cookies',
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None

def extract_cookies(domain='alphamemo.ai'):
    """Extract cookies for a specific domain from browser."""
    
    print("=" * 60)
    print("AlphaMemo Cookie Extractor".center(60))
    print("=" * 60)
    print()
    
    # Find cookies database
    print("🔍 Finding browser cookies database...")
    cookies_db = find_chrome_cookies_db()
    
    if not cookies_db:
        print("❌ Could not find Chrome/Edge cookies database!")
        print()
        print("Please make sure:")
        print("1. You have Chrome or Edge installed")
        print("2. You've logged into AlphaMemo at least once")
        print("3. The browser is closed (cookies DB is locked when browser is open)")
        return False
    
    print(f"✅ Found: {cookies_db}")
    print()
    
    # Copy to temp location (can't read while browser is running)
    temp_db = Path(os.getenv('TEMP')) / 'temp_cookies.db'
    try:
        print("📋 Copying cookies database...")
        shutil.copy2(cookies_db, temp_db)
    except Exception as e:
        print(f"❌ Failed to copy database: {e}")
        print()
        print("⚠️  Please close your browser and try again!")
        return False
    
    # Read cookies from database
    print(f"🔓 Extracting cookies for {domain}...")
    
    try:
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        
        # Query cookies
        cursor.execute("""
            SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
            FROM cookies
            WHERE host_key LIKE ?
        """, (f'%{domain}%',))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print(f"❌ No cookies found for {domain}")
            print()
            print("Please make sure you've logged into AlphaMemo first!")
            temp_db.unlink()
            return False
        
        # Convert to Playwright format
        cookies = []
        for row in rows:
            name, value, domain, path, expires, secure, httponly = row
            
            cookie = {
                'name': name,
                'value': value,
                'domain': domain,
                'path': path,
                'expires': expires / 1000000 - 11644473600 if expires > 0 else -1,  # Convert Chrome time to Unix timestamp
                'secure': bool(secure),
                'httpOnly': bool(httponly),
                'sameSite': 'Lax'
            }
            cookies.append(cookie)
        
        # Save to file
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Extracted {len(cookies)} cookies")
        print(f"💾 Saved to: {COOKIES_FILE}")
        
        # Show important cookies
        auth_cookies = [c['name'] for c in cookies if 'session' in c['name'].lower() or 'auth' in c['name'].lower() or 'token' in c['name'].lower()]
        if auth_cookies:
            print(f"🔑 Auth cookies: {', '.join(auth_cookies)}")
        
        # Cleanup
        temp_db.unlink()
        
        print()
        print("=" * 60)
        print("✅ SUCCESS!".center(60))
        print("=" * 60)
        print()
        print("The cookies have been extracted and saved!")
        print("The scraper will now be able to access AlphaMemo.")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error extracting cookies: {e}")
        if temp_db.exists():
            temp_db.unlink()
        return False

if __name__ == '__main__':
    print()
    print("⚠️  IMPORTANT: Please close your browser before running this script!")
    print("   (The cookies database is locked when the browser is open)")
    print()
    input("Press ENTER to continue...")
    print()
    
    success = extract_cookies()
    
    if not success:
        print()
        print("=" * 60)
        print("Alternative Method".center(60))
        print("=" * 60)
        print()
        print("If extraction failed, you can manually export cookies:")
        print("1. Install browser extension 'EditThisCookie' or 'Cookie-Editor'")
        print("2. Visit https://www.alphamemo.ai (while logged in)")
        print("3. Export all cookies as JSON")
        print("4. Save to: backend/.secrets/alphamemo_cookies.json")
        print()
    
    input("\nPress ENTER to exit...")

"""
AlphaMemo Token Refresh Manager.

Automatically refreshes Supabase auth tokens when they expire,
ensuring permanent access without manual re-login.
"""
import json
import time
from pathlib import Path
from typing import Dict, Optional
import requests
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

COOKIES_FILE = Path(__file__).parent.parent / '.secrets' / 'alphamemo_cookies.json'
TOKEN_METADATA_FILE = Path(__file__).parent.parent / '.secrets' / 'alphamemo_tokens.json'

# Supabase API endpoint (reverse-engineered)
SUPABASE_URL = "https://ufldzttccthnnqibebbah.supabase.co/auth/v1"


class TokenRefreshManager:
    """Manages automatic token refresh for AlphaMemo (Supabase Auth)."""
    
    def __init__(self):
        self.cookies_file = COOKIES_FILE
        self.metadata_file = TOKEN_METADATA_FILE
    
    def load_token_metadata(self) -> Optional[Dict]:
        """Load token metadata (refresh_token, expiry time)."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load token metadata: {e}")
        return None
    
    def save_token_metadata(self, data: Dict):
        """Save token metadata."""
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Token metadata saved")
        except Exception as e:
            logger.error(f"Failed to save token metadata: {e}")
    
    def extract_tokens_from_cookies(self) -> Optional[Dict]:
        """
        Extract auth tokens and refresh token from cookies.
        
        Returns:
            {
                'access_token': str,
                'refresh_token': str,
                'expires_at': int (timestamp)
            }
        """
        try:
            if not self.cookies_file.exists():
                logger.error("Cookies file not found")
                return None
            
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
            
            # Find Supabase auth tokens
            auth_token_0 = None
            auth_token_1 = None
            
            for cookie in cookies:
                name = cookie.get('name', '')
                if name == 'sb-api-auth-token.0':
                    auth_token_0 = cookie.get('value', '')
                elif name == 'sb-api-auth-token.1':
                    auth_token_1 = cookie.get('value', '')
            
            if not auth_token_0:
                logger.error("No auth token found in cookies")
                return None
            
            # Decode base64 token
            import base64
            try:
                # Remove 'base64-' prefix if exists
                token_data = auth_token_0.replace('base64-', '')
                decoded = base64.b64decode(token_data).decode('utf-8')
                token_json = json.loads(decoded)
                
                return {
                    'access_token': token_json.get('access_token'),
                    'refresh_token': token_json.get('refresh_token'),
                    'expires_at': token_json.get('expires_at')
                }
            except Exception as e:
                logger.error(f"Failed to decode auth token: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract tokens: {e}")
            return None
    
    def is_token_expired(self, expires_at: int) -> bool:
        """Check if token is expired or will expire soon."""
        # Add 5 minute buffer
        return time.time() >= (expires_at - 300)
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Supabase refresh token
        
        Returns:
            New token data or None if failed
        """
        try:
            url = f"{SUPABASE_URL}/token?grant_type=refresh_token"
            
            headers = {
                'Content-Type': 'application/json',
                'apikey': 'your-supabase-anon-key',  # TODO: Extract from page
            }
            
            data = {
                'refresh_token': refresh_token
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                logger.info("Successfully refreshed access token")
                return result
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None
    
    def update_cookies_with_new_token(self, new_token_data: Dict):
        """Update cookies file with new access token."""
        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
            
            # Encode new token
            import base64
            token_json = json.dumps(new_token_data)
            encoded = base64.b64encode(token_json.encode('utf-8')).decode('utf-8')
            new_value = f"base64-{encoded}"
            
            # Update cookie
            for cookie in cookies:
                if cookie.get('name') == 'sb-api-auth-token.0':
                    cookie['value'] = new_value
            
            # Save updated cookies
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            
            logger.info("Cookies updated with new token")
            
        except Exception as e:
            logger.error(f"Failed to update cookies: {e}")
    
    def ensure_valid_token(self) -> bool:
        """
        Ensure we have a valid access token, refreshing if necessary.
        
        Returns:
            True if valid token is available, False otherwise
        """
        try:
            # Extract current tokens
            tokens = self.extract_tokens_from_cookies()
            
            if not tokens:
                logger.error("No tokens found in cookies")
                return False
            
            # Check if expired
            if not self.is_token_expired(tokens['expires_at']):
                logger.info("Token is still valid")
                return True
            
            logger.info("Token expired, attempting refresh...")
            
            # Refresh token
            new_tokens = self.refresh_access_token(tokens['refresh_token'])
            
            if not new_tokens:
                logger.error("Token refresh failed")
                return False
            
            # Update cookies
            self.update_cookies_with_new_token(new_tokens)
            
            # Save metadata
            self.save_token_metadata({
                'last_refresh': int(time.time()),
                'expires_at': new_tokens.get('expires_at')
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring valid token: {e}")
            return False


# CLI tool
def main():
    """CLI tool to manually refresh tokens."""
    print("AlphaMemo Token Refresh Manager")
    print("="*60)
    
    manager = TokenRefreshManager()
    
    print("\n1. Extracting tokens from cookies...")
    tokens = manager.extract_tokens_from_cookies()
    
    if not tokens:
        print("❌ Failed to extract tokens")
        return
    
    print("✅ Tokens extracted")
    print(f"   Expires at: {tokens['expires_at']}")
    print(f"   Is expired: {manager.is_token_expired(tokens['expires_at'])}")
    
    print("\n2. Checking/refreshing token...")
    if manager.ensure_valid_token():
        print("✅ Token is valid")
    else:
        print("❌ Token refresh failed")


if __name__
 == '__main__':
    main()

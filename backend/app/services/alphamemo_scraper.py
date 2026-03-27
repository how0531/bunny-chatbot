"""
AlphaMemo Earnings Call Transcript Scraper.

Uses Playwright with PERSISTENT CONTEXT (Real Chrome Profile) to bypass 
anti-bot protections. Requires Chrome to be closed during execution.
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from playwright.async_api import async_playwright
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

# Chrome User Data Path (Windows)
CHROME_USER_DATA = Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data'


class AlphaMemoScraper:
    """Scraper for AlphaMemo earnings call transcripts using Real Chrome Profile."""
    
    BASE_URL = "https://www.alphamemo.ai/free-transcripts"
    
    async def _get_browser_context(self, p):
        """Launch persistent context with real Chrome profile."""
        if not CHROME_USER_DATA.exists():
            logger.error(f"Chrome user data not found at: {CHROME_USER_DATA}")
            return None
            
        try:
            # Launch persistent context
            # Note: This will FAIL if Chrome is already open
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(CHROME_USER_DATA),
                headless=True,  # Use headless=True for background service? 
                                # AlphaMemo might detect headless. Use False if needed.
                                # Let's try headless=False first as observed working in manual test.
                                # Actually, for backend service, we usually want headless.
                                # But let's stick to what we verified works: headless=False (visible)
                                # or keep it consistent with the manual test.
                channel='chrome',
                args=['--disable-blink-features=AutomationControlled']
            )
            return context
        except Exception as e:
            logger.error(f"Failed to launch Chrome (is it open?): {e}")
            return None

    async def get_recent_transcripts(
        self, 
        stock_code: str = None, 
        limit: int = 10
    ) -> List[Dict]:
        """Scrape recent transcripts using real browser session."""
        try:
            async with async_playwright() as p:
                context = await self._get_browser_context(p)
                if not context:
                    return []
                
                page = context.pages[0] if context.pages else await context.new_page()
                
                try:
                    logger.info(f"Navigating to {self.BASE_URL}...")
                    await page.goto(self.BASE_URL, wait_until='networkidle', timeout=30000)
                    
                    # Wait for grid to load
                    try:
                        await page.wait_for_selector('div.grid-cols-12', timeout=10000)
                    except Exception:
                        logger.warning("Timeout waiting for grid, checking content anyway")
                    
                    # Get HTML
                    html = await page.content()
                    
                finally:
                    # Always close context to release lock
                    await context.close()
                
                # Parse with BeautifulSoup
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'lxml')
                rows = soup.select('div.grid-cols-12')
                
                transcripts = []
                for row in rows:
                    if 'cursor-pointer' not in row.get('class', []):
                        continue
                        
                    try:
                        stock_div = row.select_one('div.col-span-3')
                        if not stock_div: continue
                        
                        name_elem = stock_div.select_one('div.font-medium')
                        code_elem = stock_div.select_one('div.text-xs')
                        
                        if not name_elem or not code_elem: continue
                        
                        code = code_elem.text.strip()
                        if stock_code and code != stock_code:
                            continue
                            
                        # Date & Duration
                        date_divs = row.select('div.col-span-2')
                        date_text = date_divs[0].text.strip() if len(date_divs) > 0 else ''
                        duration = date_divs[1].text.strip() if len(date_divs) > 1 else ''
                        
                        # URL Extraction
                        summary_url = None
                        links = row.select('a')
                        for link in links:
                            href = link.get('href', '')
                            if '/free-transcripts/' in href:
                                summary_url = f"https://www.alphamemo.ai{href}" if href.startswith('/') else href
                                break
                        
                        transcripts.append({
                            'stock_code': code,
                            'stock_name': name_elem.text.strip(),
                            'date': date_text,
                            'duration': duration,
                            'summary_url': summary_url
                        })
                        
                        if len(transcripts) >= limit: break
                        
                    except Exception as e:
                        logger.error(f"Row parse error: {e}")
                        continue
                
                logger.info(f"Scraped {len(transcripts)} transcripts")
                return transcripts

        except Exception as e:
            logger.error(f"Scrape error: {e}", exc_info=True)
            return []

    async def get_transcript_summary(self, summary_url: str) -> Dict:
        """Get transcript details using real browser session."""
        try:
            async with async_playwright() as p:
                context = await self._get_browser_context(p)
                if not context:
                    return {}
                
                page = context.pages[0] if context.pages else await context.new_page()
                
                try:
                    logger.info(f"Navigating to {summary_url}...")
                    await page.goto(summary_url, wait_until='networkidle', timeout=30000)
                    await page.wait_for_timeout(2000) # Small buffer for dynamic content
                    html = await page.content()
                finally:
                    await context.close()
                
                # Parse
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'lxml')
                summary = {'highlights': [], 'revenue': [], 'profit': [], 'outlook': [], 'risks': []}
                
                sections = soup.select('section, div[class*="section"]')
                for section in sections:
                    heading = section.select_one('h2, h3, h4, strong')
                    if not heading: continue
                    title = heading.text.strip()
                    items = [li.text.strip() for li in section.select('ul li, ol li, p') if li.text.strip()]
                    
                    if '亮點' in title or 'highlight' in title.lower(): summary['highlights'].extend(items)
                    elif '營收' in title or 'revenue' in title.lower(): summary['revenue'].extend(items)
                    elif '獲利' in title or 'profit' in title.lower(): summary['profit'].extend(items)
                    elif '展望' in title or 'outlook' in title.lower(): summary['outlook'].extend(items)
                    elif '風險' in title or 'risk' in title.lower(): summary['risks'].extend(items)
                
                # Fallback
                if not any(summary.values()):
                    summary['highlights'] = [li.text.strip() for li in soup.select('ul li')[:10]]
                    
                return summary

        except Exception as e:
            logger.error(f"Summary scrape error: {e}", exc_info=True)
            return {}

# Test function
if __name__ == '__main__':
    scraper = AlphaMemoScraper()
    print("Testing Real Browser Scraper...")
    try:
        t_list = asyncio.run(scraper.get_recent_transcripts(limit=3))
        for t in t_list:
            print(t)
    except Exception as e:
        print(f"Test failed: {e}")

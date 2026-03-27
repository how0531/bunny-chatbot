
import sys
import os
import time
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.services.stock_service import StockService
from backend.app.core.logger import setup_logger

logger = setup_logger("DailyUpdate")

def run_daily_update():
    """
    Prefetch AlphaMemo data for strong sectors to ensure instant Chat response.
    """
    print("🚀 Starting Daily Morning Update...")
    print("   (This downloads earnings data so the Chatbot can be instant)")
    
    service = StockService()
    
    # 1. Get Strong Sectors
    print("\n📊 Analyzing Strong Sectors...")
    try:
        # Fetch top 5 sectors, top 3 stocks each
        strong_sectors = service.metabase.get_strong_sectors(days=2, top_n=5)
    except Exception as e:
        print(f"❌ Failed to fetch sectors: {e}")
        return

    if not strong_sectors:
        print("⚠️ No strong sectors found today.")
        return

    # 2. Extract unique target stocks (Top 1 per sector)
    target_stocks = []
    seen = set()
    
    # Group by sector to pick top 1
    sectors_map = {}
    for item in strong_sectors:
        sec = item.get('概念名稱')
        if sec not in sectors_map:
            sectors_map[sec] = []
        sectors_map[sec].append(item)
        
    for sec, stocks in sectors_map.items():
        # Sort by return
        sorted_stocks = sorted(stocks, key=lambda x: float(x.get('漲跌幅', 0)), reverse=True)
        # Pick Top 1 (Leader)
        leader = sorted_stocks[0]
        sid = leader.get('股票代號')
        name = leader.get('股票名稱')
        
        if sid and sid not in seen:
            target_stocks.append((sid, name, sec))
            seen.add(sid)
            
    print(f"\n🎯 Targets Identified: {len(target_stocks)} stocks")
    for sid, name, sec in target_stocks:
        print(f"   - {sid} {name} ({sec})")
        
    # 3. Scrape / Prefetch
    print("\n📥 Downloading Earnings Data (AlphaMemo)...")
    print("   ⚠️ Ensure Chrome is CLOSED. Do not touch the browser that opens.")
    
    success_count = 0
    for i, (sid, name, sec) in enumerate(target_stocks, 1):
        print(f"   [{i}/{len(target_stocks)}] Fetching {sid} {name}...", end=" ", flush=True)
        try:
            # This triggers the scraper + caching
            start_time = time.time()
            data = service.get_earnings_call_insights(sid)
            duration = time.time() - start_time
            
            if data.get('found'):
                print(f"✅ Found ({duration:.1f}s)")
                success_count += 1
            else:
                print(f"⚪ No Data or error ({duration:.1f}s)")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            
        # Small pause to be gentle
        time.sleep(2)
        
    print("\n" + "="*50)
    print(f"✅ Update Complete! Success: {success_count}/{len(target_stocks)}")
    print("   The Chatbot will now respond INSTANTLY for these sectors.")
    print("="*50)

if __name__ == "__main__":
    run_daily_update()

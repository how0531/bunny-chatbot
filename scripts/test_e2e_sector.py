
import requests
import json
import time

API_URL = "http://localhost:5000/api/chat"

def test_sector_analysis():
    print("🚀 Starting End-to-End Test: Sector Analysis with AlphaMemo Data")
    print("   Wait for server to be ready...")
    time.sleep(5) 
    
    payload = {"message": "光通訊 強勢族群"}
    
    try:
        print(f"👉 Sending request: {payload}")
        print("   (Please wait... Scraping multiple stocks takes time)")
        response = requests.post(API_URL, json=payload, timeout=180)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('response', '')
            print("\n✅ Response Received!")
            print("="*60)
            print(content)
            print("="*60)
            
            # Verification Logic
            if "永豐筆記" in content:
                print("\n✅ '永豐筆記' section found.")
            else:
                print("\n❌ '永豐筆記' NOT found.")
                
            if "法說會" in content or "營收" in content or "%" in content:
                 print("✅ Specific data points detected (looks data-driven).")
            else:
                 print("⚠️ Response looks generic (check if AlphaMemo data was found).")
                 
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   (Ensure backend/run.py is running)")

if __name__ == "__main__":
    test_sector_analysis()

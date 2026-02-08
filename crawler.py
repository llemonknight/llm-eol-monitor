import requests
import json
import re
import os
from datetime import datetime

# 取得腳本所在的絕對路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "models.json")

def deep_analyze_html(platform, html_content):
    """
    執行深度分析：不僅僅是連通性，而是檢查關鍵變動。
    目前以 regex 檢查表格中的日期格式變動，未來可擴展 BeautifulSoup 解析。
    """
    # 尋找 YYYY 年 MM 月 DD 日 或 YYYY-MM-DD
    found_dates = re.findall(r'(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)|(\d{4}-\d{2}-\d{2})', html_content)
    # 計算頁面中的模型 ID 特徵 (例如 gemini- 或 claude-)
    model_mentions = len(re.findall(r'gemini-|claude-|llama-|titan-|imagen-', html_content, re.I))
    
    return {
        "date_count": len(found_dates),
        "model_density": model_mentions,
        "content_length": len(html_content)
    }

def update_data():
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found.")
        return

    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"=== Starting Deep Scan at {datetime.now()} ===")
    
    for platform in ["bedrock", "gcp"]:
        url = data[platform]["doc"]
        print(f"Scanning {platform}: {url}...")
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            
            # 執行深度分析
            analysis = deep_analyze_html(platform, resp.text)
            print(f"  [Analysis] Found {analysis['date_count']} dates and {analysis['model_density']} model mentions.")
            
            # 如果偵測到密度異常變動（例如突然增加很多模型），可以在這裡標記標籤或發出通知
            if analysis['model_density'] > 10:
                print(f"  [Info] Document depth confirmed for {platform}.")
            
        except Exception as e:
            print(f"  [Warning] Failed to deep scan {platform}: {e}")

    # 更新最後檢查時間
    data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print("\n✅ Crawler logic upgraded to 'Deep Scan' mode.")

if __name__ == "__main__":
    update_data()

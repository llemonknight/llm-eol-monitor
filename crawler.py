import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "models.json")

def scrape_aws():
    url = "https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html"
    print(f"Scraping AWS: {url}")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    
    scraped_models = {}
    for table in soup.find_all('table'):
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        if 'Model name' in headers and 'EOL date' in headers:
            name_idx = headers.index('Model name')
            eol_idx = headers.index('EOL date')
            
            for tr in table.find_all('tr')[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all('td')]
                if len(cells) > max(name_idx, eol_idx):
                    name = cells[name_idx]
                    eol_raw = cells[eol_idx]
                    
                    # Clean EOL date (e.g. "No sooner than 4/23/2025" -> "2025-04-23")
                    # But the frontend handles "No sooner than", so we just need a standard date format or keep raw if complex
                    # AWS format is usually M/D/YYYY
                    clean_date = eol_raw.replace("No sooner than ", "").strip()
                    if clean_date:
                        try:
                            dt = datetime.strptime(clean_date, "%m/%d/%Y")
                            formatted_date = dt.strftime("%Y-%m-%d")
                        except ValueError:
                            formatted_date = clean_date
                    else:
                        formatted_date = "未公布"
                        
                    scraped_models[name] = formatted_date
    return scraped_models

def scrape_gcp():
    url = "https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions?hl=zh-tw"
    print(f"Scraping GCP: {url}")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    
    scraped_models = {}
    for table in soup.find_all('table'):
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        if '模型 ID' in headers and '退役日期' in headers:
            id_idx = headers.index('模型 ID')
            date_idx = headers.index('退役日期')
            
            for tr in table.find_all('tr')[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all('td')]
                if len(cells) > max(id_idx, date_idx):
                    model_id = cells[id_idx].replace("*", "").strip()
                    date_raw = cells[date_idx].strip()
                    
                    if "未公布" in date_raw:
                        formatted_date = "未公布"
                    else:
                        # Format "2026 年 12 月 13 日" -> "2026-12-13"
                        clean = date_raw.replace("年", "-").replace("月", "-").replace("日", "").replace(" ", "")
                        parts = clean.split("-")
                        if len(parts) == 3:
                            formatted_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                        else:
                            formatted_date = date_raw
                            
                    scraped_models[model_id] = formatted_date
    return scraped_models

def update_data():
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found.")
        return

    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"=== Starting Smart Sync at {datetime.now()} ===")
    
    try:
        aws_data = scrape_aws()
        gcp_data = scrape_gcp()
        
        updates_made = 0
        
        # Update AWS models
        for m in data['bedrock']['models']:
            # Try exact match or partial match
            matched_date = None
            if m['n'] in aws_data:
                matched_date = aws_data[m['n']]
            else:
                for k, v in aws_data.items():
                    if k.lower() in m['n'].lower() or m['n'].lower() in k.lower():
                        matched_date = v
                        break
            
            if matched_date and m['d'] != matched_date and matched_date != "未公布":
                print(f"  [AWS Update] {m['n']}: {m['d']} -> {matched_date}")
                m['d'] = matched_date
                updates_made += 1

        # Update GCP models
        for m in data['gcp']['models']:
            matched_date = None
            # Need to handle combined names like "gemini-1.5-pro-001 / 002"
            parts = [p.strip() for p in m['n'].split('/')]
            for p in parts:
                search_key = p if "gemini" in p or "imagen" in p else m['n'].split('-')[0] + "-" + p
                for k, v in gcp_data.items():
                    if k == search_key or k == m['n'] or p in k:
                        matched_date = v
                        break
                if matched_date:
                    break
            
            if matched_date and m['d'] != matched_date and matched_date != "未公布":
                print(f"  [GCP Update] {m['n']}: {m['d']} -> {matched_date}")
                m['d'] = matched_date
                updates_made += 1

        if updates_made > 0:
            print(f"Successfully updated {updates_made} model dates.")
        else:
            print("All models are up to date.")
            
    except Exception as e:
        print(f"[Error] Failed to scrape: {e}")

    # Update timestamp
    data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print("\n✅ Crawler logic upgraded to 'BeautifulSoup Smart Sync' mode.")

if __name__ == "__main__":
    update_data()

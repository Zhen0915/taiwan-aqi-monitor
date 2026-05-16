import os
import requests
import csv
import io
from bs4 import BeautifulSoup
from models import db, AirQualityRecord

# 關閉 SSL 警告
os.environ['CURL_CA_BUNDLE'] = ''
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def safe_int(value, default=0):
    if value is None or value == '':
        return default
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return default


def get_latest_csv_url():
    """從 data.gov.tw 抓取最新的 CSV 下載網址"""
    print("🔍 正在從 data.gov.tw 取得最新 CSV 網址...")
    url = "https://data.gov.tw/dataset/40448"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找 CSV 下載連結
        for a in soup.find_all('a', href=True):
            href = a['href']
            if ('aqx_p_432' in href or 'CSV' in a.get_text()) and 'format=CSV' in href:
                print(f"✅ 找到最新 CSV 網址: {href[:120]}...")
                return href
                
        print("⚠️ 找不到最新 CSV 連結，使用備用網址")
        
    except Exception as e:
        print(f"❌ 抓取 data.gov.tw 失敗: {e}")
    
    # 備用網址（不含 api_key）
    return "https://data.moenv.gov.tw/api/v2/aqx_p_432?limit=1000&sort=ImportDate%20desc&format=CSV"


def fetch_live_aqi_csv_data():
    """主要更新函式"""
    print("🚀 正在下載最新空氣品質 CSV 資料...")
    
    csv_url = get_latest_csv_url()
    
    try:
        response = requests.get(csv_url, timeout=30, verify=False)
        if response.status_code != 200:
            print(f"❌ 下載失敗，狀態碼: {response.status_code}")
            return False

        csv_file = io.StringIO(response.text)
        csv_reader = csv.DictReader(csv_file)

        # 清空舊資料
        db.create_all()
        db.session.query(AirQualityRecord).delete()
        db.session.commit()

        success_count = 0
        latest_time = ""
        
        for row in csv_reader:
            try:
                publishtime = str(row.get('publishtime', '')).strip()
                if publishtime:
                    latest_time = publishtime
                
                record = AirQualityRecord(
                    sitename=str(row.get('sitename', '未知')).strip(),
                    county=str(row.get('county', '未知')).strip(),
                    aqi=safe_int(row.get('aqi')),
                    status=str(row.get('status', '未知')).strip(),
                    pm25=safe_int(row.get('pm2.5') or row.get('pm25')),
                    publishtime=publishtime
                )
                db.session.add(record)
                success_count += 1
            except:
                continue

        db.session.commit()
        print(f"🎉 成功寫入 {success_count} 筆資料！最新資料時間: {latest_time}")
        return True

    except Exception as e:
        print(f"❌ 資料處理失敗: {e}")
        return False


if __name__ == '__main__':
    from app import app
    with app.app_context():
        fetch_live_aqi_csv_data()
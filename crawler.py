import os
os.environ['CURL_CA_BUNDLE'] = '' # 關閉全域憑證嚴格比對

import requests
import urllib3
import csv
import io
from models import db, AirQualityRecord

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def safe_int(value, default=0):
    if value is None: return default
    try: return int(float(str(value).strip()))
    except (ValueError, TypeError): return default

def fetch_live_aqi_csv_data():
    """下載政府即時 CSV 檔案並寫入資料庫"""
    print("🚀 正在連線環境部下載全台即時空氣品質 CSV 檔案...")
    csv_url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key=e8dd42e6-9b8b-43f8-983e-e86bc6a31c3f&limit=1000&sort=ImportDate desc&format=CSV"
    
    response = requests.get(csv_url, timeout=15, verify=False)
    if response.status_code != 200:
        print(f"❌ 連線失敗，錯誤碼: {response.status_code}")
        return
        
    csv_file = io.StringIO(response.text)
    csv_reader = csv.DictReader(csv_file)

    # 強制建立資料表並清空舊資料
    db.create_all()
    db.session.query(AirQualityRecord).delete()
    
    success_count = 0
    for row in csv_reader:
        sitename = row.get('sitename', '未知')
        county = row.get('county', '未知')
        aqi_val = row.get('aqi')
        status = row.get('status', '未知')
        pm25_val = row.get('pm2.5') or row.get('pm25')
        publishtime = row.get('publishtime', '')

        if aqi_val and str(aqi_val).strip():
            record = AirQualityRecord(
                sitename=str(sitename).strip(),
                county=str(county).strip(),
                aqi=safe_int(aqi_val),
                status=str(status).strip(),
                pm25=safe_int(pm25_val),
                publishtime=str(publishtime).strip()
            )
            db.session.add(record)
            success_count += 1
    
    db.session.commit()
    print(f"🎉 [大功告成] 成功讀取 CSV 並將 {success_count} 筆空氣品質數據同步至雲端資料庫！")

if __name__ == '__main__':
    # 這樣本機執行 python crawler.py 依然可以單獨運作
    from app import app
    with app.app_context():
        fetch_live_aqi_csv_data()
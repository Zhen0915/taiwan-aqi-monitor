import requests
import urllib3
import csv
import io
from app import app
from models import db, AirQualityRecord

# 關閉因忽略 SSL 憑證產生的警告訊息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def safe_int(value, default=0):
    if value is None:
        return default
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return default

def fetch_live_aqi_csv_data():
    print("🚀 [開始執行] 正在連線環境部下載全台即時空氣品質 CSV 檔案...")
    
    # 環境部官方提供的免費即時 AQI CSV 檔案下載連結
    csv_url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key=e75b1660-e564-4107-aad5-a8be1f905dd9&limit=1000&sort=ImportDate desc&format=CSV"
    
    try:
        # 下載 CSV 檔案內容
        response = requests.get(csv_url, timeout=15, verify=False)
        
        if response.status_code != 200:
            print(f"❌ 連線失敗，政府 CSV 伺服器回應錯誤碼: {response.status_code}")
            return
            
        print("📋 [CSV 下載成功] 開始解析並清洗資料...")

        # 將下載下來的文字轉換成 Python 可以一行一行讀取的 CSV 串流
        csv_file = io.StringIO(response.text)
        csv_reader = csv.DictReader(csv_file) # 自動將第一行當作欄位名稱

        with app.app_context():
            # 強制建立資料表（防禦機制）
            db.create_all()
            
            # 清空舊資料
            db.session.query(AirQualityRecord).delete()
            
            success_count = 0
            
            # 一行一行讀取 CSV 的資料
            for row in csv_reader:
                # 擷取 CSV 的欄位名稱
                sitename = row.get('sitename', '未知')
                county = row.get('county', '未知')
                aqi_val = row.get('aqi')
                status = row.get('status', '未知')
                pm25_val = row.get('pm2.5') or row.get('pm25')
                publishtime = row.get('publishtime', '')

                # 只要有 AQI 指標就塞進資料庫
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

    except Exception as e:
        print(f"💥 處理 CSV 資料時發生非預期錯誤: {e}")

if __name__ == '__main__':
    fetch_live_aqi_csv_data()
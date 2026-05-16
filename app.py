import os
# 💡 【核心修正】：強制全域關閉 Python 的 SSL 憑證嚴格比對，徹底解決政府網站憑證過期導致自動爬蟲被阻斷的問題
os.environ['CURL_CA_BUNDLE'] = ''

import requests
import urllib3
import csv
import io
from flask import Flask, render_template, request
from models import db, AirQualityRecord
from sqlalchemy import func

# 關閉 SSL 警告訊息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# 記得確保換成你的 postgresql 網址，並加上 ?sslmode=require
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'postgresql://zhen:caIZBXsNJJD4FENZn9FiSr5QqLrqQRdF@dpg-d846lk0jo89c73ajcf9g-a.singapore-postgres.render.com/traffic_data_09yl?sslmode=require'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def safe_int(value, default=0):
    if value is None: return default
    try: return int(float(str(value).strip()))
    except (ValueError, TypeError): return default

def auto_fetch_data_right_now():
    """每次用戶進網頁時自動觸發的即時採購功能"""
    csv_url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key=e8dd42e6-9b8b-43f8-983e-e86bc6a31c3f&limit=1000&sort=ImportDate desc&format=CSV"
    
    try:
        print("🔄 [自動同步] 正在為造訪用戶動態下載環境部最新空品數據...")
        # 設定 8 秒超時，避免政府伺服器塞車讓用戶等太久
        response = requests.get(csv_url, timeout=8, verify=False)
        
        if response.status_code == 200:
            csv_file = io.StringIO(response.text)
            csv_reader = csv.DictReader(csv_file)
            
            # 確保資料表存在
            db.create_all()
            # 清空舊快取資料
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
            print(f"🎉 [自動同步成功] 已成功更新 {success_count} 筆最新即時數據！")
        else:
            print(f"⚠️ [自動同步跳過] 政府伺服器回應代碼 {response.status_code}，維持展示資料庫現有快取。")
            
    except Exception as e:
        # 即使自動同步發生任何網路意外（例如政府塞車），也絕對不讓網頁崩潰，而是優雅地下載資料庫既有的快取
        print(f"❌ [自動同步暫時繞過] 遭遇網路震盪或憑證阻斷: {e}。系統啟動容錯機制，改由資料庫快取供貨。")

@app.route('/')
def home():
    # 每次客人進來，先嘗試自動採購最新鮮的
    auto_fetch_data_right_now()

    # 1. 撈出所有不重複的縣市清單
    all_counties = db.session.query(AirQualityRecord.county).distinct().all()
    county_list = [c[0] for c in all_counties if c[0]]
    county_list.sort()

    selected_county = request.args.get('county', '').strip()

    # 2. 進行數據處理與聚合統計
    if selected_county:
        records = AirQualityRecord.query.filter_by(county=selected_county).order_by(AirQualityRecord.aqi.desc()).all()
        avg_stats = db.session.query(func.avg(AirQualityRecord.aqi)).filter_by(county=selected_county).first()
        max_pm25 = db.session.query(func.max(AirQualityRecord.pm25)).filter_by(county=selected_county).scalar() or 0
    else:
        records = AirQualityRecord.query.order_by(AirQualityRecord.aqi.desc()).all()
        avg_stats = db.session.query(func.avg(AirQualityRecord.aqi)).first()
        max_pm25 = db.session.query(func.max(AirQualityRecord.pm25)).scalar() or 0

    avg_aqi = round(avg_stats[0], 1) if avg_stats[0] is not None else 0
    
    time_record = AirQualityRecord.query.first()
    update_time = time_record.publishtime if time_record else "未知"

    return render_template(
        'index.html',
        records=records,
        county_list=county_list,
        selected_county=selected_county,
        avg_aqi=avg_aqi,
        max_pm25=max_pm25,
        update_time=update_time
    )

if __name__ == '__main__':
    app.run(debug=True)
import os
import requests
import urllib3
import csv
import io
from flask import Flask, render_template, request
from models import db, AirQualityRecord
from sqlalchemy import func

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://zhen:caIZBXsNJJD4FENZn9FiSr5QqLrqQRdF@dpg-d846lk0jo89c73ajcf9g-a.singapore-postgres.render.com/traffic_data_09yl')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def safe_int(value, default=0):
    if value is None: return default
    try: return int(float(str(value).strip()))
    except (ValueError, TypeError): return default

# 💡 新增：讓店長自己具備採購功能
def auto_fetch_data_right_now():
    csv_url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key=e75b1660-e564-4107-aad5-a8be1f905dd9&limit=1000&sort=Import Datedesc&format=CSV"
    try:
        response = requests.get(csv_url, timeout=10, verify=False)
        if response.status_code == 200:
            csv_file = io.StringIO(response.text)
            csv_reader = csv.DictReader(csv_file)
            
            db.create_all()
            db.session.query(AirQualityRecord).delete()
            
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
            db.session.commit()
            print("🔄 [雲端同步] 偵測到用戶造訪，已成功向環境部同步最新數據！")
    except Exception as e:
        print(f"💥 自動同步失敗: {e}")

@app.route('/')
def home():
    # 💡 核心改動：每次有人開網頁，先自動執行採購，確保冰箱永遠是最新鮮的！
    auto_fetch_data_right_now()

    # 1. 撈出所有不重複的縣市清單
    all_counties = db.session.query(AirQualityRecord.county).distinct().all()
    county_list = [c[0] for c in all_counties if c[0]]
    county_list.sort()

    selected_county = request.args.get('county', '').strip()

    # 2. 進行數據處理
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
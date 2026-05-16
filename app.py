import os
from flask import Flask, render_template, request
from models import db, AirQualityRecord
from sqlalchemy import func

# 💡 引入我們另一個檔案 crawler.py 的抓資料功能
from crawler import fetch_live_aqi_csv_data

app = Flask(__name__)

# 記得更換成你的資料庫連線網址（注意改為 postgresql:// 開頭與加上 ?sslmode=require）
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'postgresql://zhen:caIZBXsNJJD4FENZn9FiSr5QqLrqQRdF@dpg-d846lk0jo89c73ajcf9g-a.singapore-postgres.render.com/traffic_data_09yl?sslmode=require'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# 💡 【核心修正】：當 Render 啟動 app.py 時，順便自動執行一次 crawler.py 的功能！
with app.app_context():
    try:
        print("🚀 [系統啟動] 正在執行初始化資料庫同步...")
        fetch_live_aqi_csv_data()
    except Exception as e:
        print(f"⚠️ 初始化資料同步失敗: {e}")

@app.route('/')
def home():
    # 這裡回歸純粹，客人來了直接拿冰箱現成的貨，網頁一秒開啟，不再卡頓！
    
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
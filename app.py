import os
from flask import Flask, render_template, request
from models import db, AirQualityRecord
from sqlalchemy import func, create_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# 引入 crawler
from crawler import fetch_live_aqi_csv_data

app = Flask(__name__)

# ====================== 資料庫設定（加強 SSL 與 Pooling） ======================
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and 'sslmode' not in DATABASE_URL:
    DATABASE_URL += '?sslmode=require'

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,      # 防止使用無效連線
    "pool_recycle": 1800,       # 每 30 分鐘回收連線
    "pool_size": 5,
    "max_overflow": 10,
}

db.init_app(app)

# ====================== 定時更新排程 ======================
scheduler = BackgroundScheduler()

def update_aqi_data():
    """背景更新 - 使用獨立 session 避免 SSL 衝突"""
    try:
        # 每次更新都建立獨立連線
        with app.app_context():
            print("🔄 [定時更新] 開始執行...")
            success = fetch_live_aqi_csv_data()
            if success:
                print("✅ [定時更新] 資料更新成功！")
            else:
                print("⚠️ [定時更新] 更新失敗")
    except Exception as e:
        print(f"❌ [定時更新] 發生錯誤: {e}")

# 每 30 分鐘更新一次
scheduler.add_job(update_aqi_data, 'interval', minutes=30, id='update_aqi')
scheduler.start()

atexit.register(lambda: scheduler.shutdown(wait=False))

# ====================== 啟動時更新 ======================
with app.app_context():
    try:
        print("🚀 [系統啟動] 正在執行初始化資料同步...")
        update_aqi_data()
    except Exception as e:
        print(f"⚠️ 初始化失敗: {e}")

# ====================== 路由 ======================
@app.route('/')
def home():
    all_counties = db.session.query(AirQualityRecord.county).distinct().all()
    county_list = [c[0] for c in all_counties if c[0]]
    county_list.sort()

    selected_county = request.args.get('county', '').strip()

    if selected_county:
        records = AirQualityRecord.query.filter_by(county=selected_county)\
                    .order_by(AirQualityRecord.aqi.desc()).all()
        avg_stats = db.session.query(func.avg(AirQualityRecord.aqi))\
                    .filter_by(county=selected_county).first()
        max_pm25 = db.session.query(func.max(AirQualityRecord.pm25))\
                    .filter_by(county=selected_county).scalar() or 0
    else:
        records = AirQualityRecord.query.order_by(AirQualityRecord.aqi.desc()).all()
        avg_stats = db.session.query(func.avg(AirQualityRecord.aqi)).first()
        max_pm25 = db.session.query(func.max(AirQualityRecord.pm25)).scalar() or 0

    avg_aqi = round(avg_stats[0], 1) if avg_stats and avg_stats[0] is not None else 0
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


@app.route('/update')
def manual_update():
    update_aqi_data()
    return "✅ 已強制更新資料！<br><a href='/'>← 返回首頁</a>"


if __name__ == '__main__':
    app.run(debug=True)
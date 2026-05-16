import os
from flask import Flask, render_template, request
from models import db, AirQualityRecord
from sqlalchemy import func
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# 引入 crawler
from crawler import fetch_live_aqi_csv_data

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'postgresql://zhen:caIZBXsNJJD4FENZn9FiSr5QqLrqQRdF@dpg-d846lk0jo89c73ajcf9g-a.singapore-postgres.render.com/traffic_data_09yl?sslmode=require'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ====================== 定時更新功能 ======================
scheduler = BackgroundScheduler()

def update_aqi_data():
    """背景定時更新空氣品質資料"""
    with app.app_context():
        try:
            print("🔄 [定時更新] 正在抓取最新空氣品質資料...")
            fetch_live_aqi_csv_data()
            print("✅ [定時更新] 資料更新完成！")
        except Exception as e:
            print(f"❌ [定時更新] 失敗: {e}")

# 每 10 分鐘更新一次（可自行調整）
scheduler.add_job(update_aqi_data, 'interval', minutes=10, id='update_aqi')
scheduler.start()

# 確保 Render 關閉時正確結束 scheduler
atexit.register(lambda: scheduler.shutdown(wait=False))

# ====================== 啟動時先更新一次 ======================
with app.app_context():
    try:
        print("🚀 [系統啟動] 正在執行初始化資料同步...")
        update_aqi_data()
    except Exception as e:
        print(f"⚠️ 初始化資料同步失敗: {e}")

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
    """手動強制更新路由（方便測試）"""
    update_aqi_data()
    return "✅ 空氣品質資料已強制更新！<br><a href='/'>← 返回首頁</a>"


if __name__ == '__main__':
    app.run(debug=True)
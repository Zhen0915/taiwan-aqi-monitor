from flask import Flask, render_template, request
from models import db, AirQualityRecord
from sqlalchemy import func

app = Flask(__name__)

# 記得保持你在步驟 2 複製的 Render PostgreSQL 外部連線字串
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://zhen:caIZBXsNJJD4FENZn9FiSr5QqLrqQRdF@dpg-d846lk0jo89c73ajcf9g-a.singapore-postgres.render.com/traffic_data_09yl'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def home():
    # 1. 撈出所有不重複的縣市清單供下拉選單使用
    all_counties = db.session.query(AirQualityRecord.county).distinct().all()
    county_list = [c[0] for c in all_counties if c[0]]
    county_list.sort()

    selected_county = request.args.get('county', '').strip()

    # 2. 進行數據聚合分析 (計算平均 AQI 展現分析實力)
    if selected_county:
        # 篩選特定縣市的測站明細
        records = AirQualityRecord.query.filter_by(county=selected_county).order_by(AirQualityRecord.aqi.desc()).all()
        
        # 計算該縣市平均 AQI
        avg_stats = db.session.query(func.avg(AirQualityRecord.aqi)).filter_by(county=selected_county).first()
        max_pm25 = db.session.query(func.max(AirQualityRecord.pm25)).filter_by(county=selected_county).scalar() or 0
    else:
        # 全台灣總覽：顯示全台最新所有測站
        records = AirQualityRecord.query.order_by(AirQualityRecord.aqi.desc()).all()
        avg_stats = db.session.query(func.avg(AirQualityRecord.aqi)).first()
        max_pm25 = db.session.query(func.max(AirQualityRecord.pm25)).scalar() or 0

    avg_aqi = round(avg_stats[0], 1) if avg_stats[0] is not None else 0
    
    # 抓取最新的發布時間（隨便抓一筆看時間即可）
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
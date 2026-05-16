from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class AirQualityRecord(db.Model):
    __tablename__ = 'air_quality_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sitename = db.Column(db.String(50), nullable=False)   # 測站名稱（如：萬華、西屯）
    county = db.Column(db.String(50), nullable=False)     # 所屬縣市（如：臺北市、臺中市）
    aqi = db.Column(db.Integer, default=0)                # 空氣品質指標 (AQI)
    status = db.Column(db.String(20))                     # 狀態（如：良好、普通、對敏感族群不健康）
    pm25 = db.Column(db.Integer, default=0)               # PM2.5 濃度
    publishtime = db.Column(db.String(50))                # 政府發布時間

    def __repr__(self):
        return f"<AirQuality {self.county}-{self.sitename} AQI:{self.aqi}>"
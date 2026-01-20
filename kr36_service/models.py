from sqlalchemy import Column, Integer, String, Text, BigInteger, DateTime
from database import Base
import datetime

class NewsFlash(Base):
    __tablename__ = "news_flash_36kr"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(BigInteger, unique=True, index=True)  # 36Kr 的原始 ID
    title = Column(String(500), index=True)
    content = Column(Text)
    publish_time = Column(DateTime, index=True)  # 发布时间
    created_at = Column(DateTime, default=datetime.datetime.now)  # 抓取入库时间
    source_url = Column(String(1000))

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import uvicorn
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import get_db, SessionLocal, engine, Base
from models import NewsFlash
from fetcher import Kr36Fetcher

# 初始化数据库
Base.metadata.create_all(bind=engine)

app = FastAPI(title="36Kr News Flash Service")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fetcher = Kr36Fetcher()

# 定时任务：每天晚上 10 点抓取
def scheduled_fetch():
    print(f"[{datetime.now()}] 执行定时抓取任务...")
    fetcher.fetch_latest()

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_fetch, CronTrigger(hour=22, minute=0))
scheduler.start()

import threading

# ... existing code ...

@app.on_event("startup")
async def startup_event():
    # 首次启动检查：如果库里没数据或数据较少，异步抓取过去 10 天的
    def initial_fetch():
        db = SessionLocal()
        try:
            count = db.query(NewsFlash).count()
            if count < 100:
                print("数据量较少，开始异步抓取历史数据...")
                fetcher.fetch_history(days=10)
            else:
                print("已有足够数据，抓取最新快讯...")
                fetcher.fetch_latest()
        finally:
            db.close()
    
    # 使用线程运行，避免阻塞 startup 事件导致服务无法启动
    threading.Thread(target=initial_fetch, daemon=True).start()

@app.get("/api/news")
async def get_news(
    q: Optional[str] = Query(None, description="关键词搜索"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(NewsFlash)
    if q:
        query = query.filter(
            or_(
                NewsFlash.title.ilike(f"%{q}%"),
                NewsFlash.content.ilike(f"%{q}%")
            )
        )
    
    total = query.count()
    items = query.order_by(NewsFlash.publish_time.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "items": items
    }

@app.get("/", response_class=HTMLResponse)
async def index():
    static_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_path):
        with open(static_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>36Kr News Service Frontend not found</h1>"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8007)

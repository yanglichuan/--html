import requests
import json
import time
import datetime
from sqlalchemy.orm import Session
from models import NewsFlash
from database import SessionLocal, engine, Base

# 初始化数据库表
Base.metadata.create_all(bind=engine)

class Kr36Fetcher:
    def __init__(self):
        self.url = "https://gateway.36kr.com/api/mis/nav/newsflash/list"
        self.headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://36kr.com",
            "referer": "https://36kr.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }

    def _get_payload(self, page_callback=None):
        payload = {
            "partner_id": "web",
            "timestamp": int(time.time() * 1000),
            "param": {
                "pageSize": 20,
                "pageEvent": 1 if page_callback else 0,
                "siteId": 1,
                "type": 0,
                "platformId": 2
            }
        }
        if page_callback:
            payload["param"]["pageCallback"] = page_callback
        return payload

    def fetch_page(self, page_callback=None):
        payload = self._get_payload(page_callback)
        try:
            response = requests.post(self.url, headers=self.headers, data=json.dumps(payload), timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None

    def save_items(self, items, db: Session):
        new_count = 0
        duplicate_count = 0
        for item in items:
            material = item.get("templateMaterial", {})
            item_id = item.get("itemId")
            if not item_id: continue

            # 检查是否已存在
            existing = db.query(NewsFlash).filter(NewsFlash.item_id == item_id).first()
            if existing:
                duplicate_count += 1
                continue

            pub_time_ms = material.get("publishTime")
            pub_time = datetime.datetime.fromtimestamp(pub_time_ms / 1000) if pub_time_ms else datetime.datetime.now()

            news = NewsFlash(
                item_id=item_id,
                title=material.get("widgetTitle"),
                content=material.get("widgetContent"),
                publish_time=pub_time,
                source_url=material.get("sourceUrlRoute")
            )
            db.add(news)
            new_count += 1
        
        db.commit()
        return new_count, duplicate_count

    def fetch_latest(self):
        print(f"[{datetime.datetime.now()}] 开始抓取最新快讯...")
        db = SessionLocal()
        total_new = 0
        current_callback = None
        
        try:
            while True:
                data = self.fetch_page(current_callback)
                if not data or data.get("code") != 0:
                    break
                
                res_data = data.get("data", {})
                items = res_data.get("itemList", [])
                if not items:
                    break
                
                new_count, dup_count = self.save_items(items, db)
                total_new += new_count
                
                print(f"本页抓取: {len(items)} 条, 新增: {new_count} 条, 重复: {dup_count} 条")
                
                # 如果本页出现了重复项，说明已经接上了之前的记录，停止抓取
                if dup_count > 0:
                    break
                
                current_callback = res_data.get("pageCallback")
                if not current_callback or not res_data.get("hasNextPage"):
                    break
                
                time.sleep(0.5)
            
            print(f"抓取完成，共计新增 {total_new} 条数据")
            return total_new
        finally:
            db.close()

    def fetch_history(self, days=10):
        print(f"开始抓取过去 {days} 天的历史快讯...")
        db = SessionLocal()
        target_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        current_callback = None
        total_new = 0
        
        while True:
            data = self.fetch_page(current_callback)
            if not data or data.get("code") != 0:
                break
            
            res_data = data.get("data", {})
            items = res_data.get("itemList", [])
            if not items:
                break
            
            new_count, _ = self.save_items(items, db)
            total_new += new_count
            
            # 检查最后一条的时间
            last_item_ms = items[-1].get("templateMaterial", {}).get("publishTime")
            if last_item_ms:
                last_date = datetime.datetime.fromtimestamp(last_item_ms / 1000)
                print(f"当前抓取到: {last_date}, 目标: {target_date}")
                if last_date < target_date:
                    print("已达到目标日期，停止历史抓取")
                    break
            
            current_callback = res_data.get("pageCallback")
            if not current_callback or not res_data.get("hasNextPage"):
                break
            
            time.sleep(1)  # 稍微限制频率
            
        db.close()
        print(f"历史数据抓取完成，共计入库 {total_new} 条数据")
        return total_new

if __name__ == "__main__":
    fetcher = Kr36Fetcher()
    fetcher.fetch_latest()

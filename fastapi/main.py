from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 数据库连接配置 (PostgreSQL)
SQLALCHEMY_DATABASE_URL = "postgresql://fastapi_user:fastapi_pass@localhost/fastapi_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy 模型
class ItemDB(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    description = Column(String, nullable=True)

# 创建表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FastAPI PostgreSQL 示例项目",
    description="这是一个使用 PostgreSQL 存储、SQLAlchemy ORM 的增删改查示例",
    version="1.1.0",
    root_path="/fastapi"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic 模型
class ItemBase(BaseModel):
    name: str
    price: float
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int

    class Config:
        orm_mode = True

# 依赖项：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["基础"])
async def read_root():
    return {"message": "欢迎使用 FastAPI PostgreSQL 示例接口", "docs": "/docs"}

@app.get("/items", response_model=List[ItemResponse], tags=["商品管理"])
async def read_items(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """获取商品列表"""
    items = db.query(ItemDB).offset(skip).limit(limit).all()
    return items

@app.get("/items/{item_id}", response_model=ItemResponse, tags=["商品管理"])
async def read_item(item_id: int, db: Session = Depends(get_db)):
    """获取单个商品详情"""
    item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return item

@app.post("/items", response_model=ItemResponse, tags=["商品管理"])
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """新增商品"""
    db_item = ItemDB(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/items/{item_id}", response_model=ItemResponse, tags=["商品管理"])
async def update_item(item_id: int, item: ItemCreate, db: Session = Depends(get_db)):
    """更新商品"""
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    for key, value in item.dict().items():
        setattr(db_item, key, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}", tags=["商品管理"])
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    """删除商品"""
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    db.delete(db_item)
    db.commit()
    return {"message": "删除成功"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4001)

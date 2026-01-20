from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="FastAPI 丰富示例项目",
    description="这是一个包含增删改查、数据校验和 Swagger 文档的丰富 FastAPI 示例",
    version="1.0.0",
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

# 模拟数据库
items_db = [
    {"id": 1, "name": "苹果", "price": 5.5, "description": "新鲜的红富士"},
    {"id": 2, "name": "香蕉", "price": 3.2, "description": "进口香蕉"},
]

# 数据模型
class Item(BaseModel):
    name: str
    price: float
    description: Optional[str] = None

class ItemResponse(Item):
    id: int

@app.get("/", tags=["基础"])
async def read_root():
    return {"message": "欢迎使用 FastAPI 示例接口", "docs": "/docs"}

@app.get("/items", response_model=List[ItemResponse], tags=["商品管理"])
async def read_items(skip: int = 0, limit: int = 10):
    """获取商品列表"""
    return items_db[skip : skip + limit]

@app.get("/items/{item_id}", response_model=ItemResponse, tags=["商品管理"])
async def read_item(item_id: int):
    """获取单个商品详情"""
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="商品不存在")

@app.post("/items", response_model=ItemResponse, tags=["商品管理"])
async def create_item(item: Item):
    """新增商品"""
    new_id = max([i["id"] for i in items_db]) + 1 if items_db else 1
    new_item = {"id": new_id, **item.dict()}
    items_db.append(new_item)
    return new_item

@app.put("/items/{item_id}", response_model=ItemResponse, tags=["商品管理"])
async def update_item(item_id: int, item: Item):
    """更新商品"""
    for index, existing_item in enumerate(items_db):
        if existing_item["id"] == item_id:
            updated_item = {"id": item_id, **item.dict()}
            items_db[index] = updated_item
            return updated_item
    raise HTTPException(status_code=404, detail="商品不存在")

@app.delete("/items/{item_id}", tags=["商品管理"])
async def delete_item(item_id: int):
    """删除商品"""
    for index, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db.pop(index)
            return {"message": "删除成功"}
    raise HTTPException(status_code=404, detail="商品不存在")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4001)

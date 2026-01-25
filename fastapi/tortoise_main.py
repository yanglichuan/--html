from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from tortoise import fields, models
from tortoise.contrib.fastapi import register_tortoise
import uvicorn

# 1. 定义 Tortoise 模型
class Item(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    price = fields.FloatField()
    description = fields.TextField(null=True)

    class Meta:
        table = "items"

# 2. 手动定义 Pydantic 模型
class ItemSchema(BaseModel):
    id: int
    name: str
    price: float
    description: Optional[str] = None

    class Config:
        orm_mode = True  # Pydantic v1 写法，允许从 ORM 对象初始化
        # from_attributes = True # Pydantic v2 写法

class ItemCreate(BaseModel):
    name: str
    price: float
    description: Optional[str] = None

app = FastAPI(
    title="FastAPI Tortoise ORM 示例项目",
    description="这是一个使用 Tortoise ORM 的异步增删改查示例",
    version="1.0.0"
)

# 3. 注册 Tortoise ORM
# 这会自动处理连接池的生命周期和数据库表的创建
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["__main__"]},
    generate_schemas=True,
    add_exception_handlers=True,
)

@app.get("/", tags=["基础"])
async def read_root():
    return {"message": "欢迎使用 FastAPI Tortoise ORM 示例接口", "docs": "/docs"}

@app.get("/items", response_model=List[ItemSchema], tags=["商品管理"])
async def read_items():
    """获取商品列表"""
    # Item.all() 返回的是 QuerySet，需要 await 执行
    return await Item.all()

@app.get("/items/{item_id}", response_model=ItemSchema, tags=["商品管理"])
async def read_item(item_id: int):
    """获取单个商品详情"""
    item = await Item.get_or_none(id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/items", response_model=ItemSchema, tags=["商品管理"])
async def create_item(item: ItemCreate):
    """新增商品"""
    # 将 Pydantic 模型的 dict 传给 ORM 的 create 方法
    item_obj = await Item.create(**item.dict(exclude_unset=True))
    return item_obj

@app.put("/items/{item_id}", response_model=ItemSchema, tags=["商品管理"])
async def update_item(item_id: int, item: ItemCreate):
    """更新商品"""
    # 先更新
    await Item.filter(id=item_id).update(**item.dict(exclude_unset=True))
    # 再获取更新后的对象
    item_obj = await Item.get_or_none(id=item_id)
    if not item_obj:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_obj

@app.delete("/items/{item_id}", tags=["商品管理"])
async def delete_item(item_id: int):
    """删除商品"""
    deleted_count = await Item.filter(id=item_id).delete()
    if not deleted_count:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return {"message": f"Deleted item {item_id}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4002)

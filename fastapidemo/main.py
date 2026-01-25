from datetime import datetime, time, timedelta
from typing import Annotated, Union
from uuid import UUID

from fastapi import Body, FastAPI, Query
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None

items = []

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    if item_id < 0 or item_id >= len(items):
        return {"error": "item not found"}
    item = items[item_id]
    return {"item_id": item_id, "item": item, "q": q}

@app.post("/items/")
def create_item(item: Item):
    items.append(item.model_dump())
    return {"item_id": len(items) - 1, "status": "created"}

@app.get("/items/")
def list_items(limit: int = 10):
    return {"items": items[:limit]}

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    if item_id < 0 or item_id >= len(items):
        return {"error": "item not found"}
    items[item_id] = item.model_dump()
    return {"item_id": item_id, "status": "updated"}

# 路径参数示例：不指定类型（默认为字符串）
@app.get("/users/{user_id}")
async def read_user(user_id):
    return {"user_id": user_id}

# 路径参数示例：指定类型
@app.get("/models/{model_name}")
async def get_model(model_name: str):
    return {"model_name": model_name}

# 查询参数示例
fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]

@app.get("/items-list/")
async def read_items_list(skip: int = 0, limit: int = 10):
    return fake_items_db[skip : skip + limit]

# 使用 Query 进行显式声明和校验
@app.get("/items-query/")
async def read_items_query(
    q: Annotated[
        Union[str, None], 
        Query(
            alias="item-query",
            title="查询字符串",
            description="用于搜索条目的查询参数，长度需在 3 到 10 之间",
            min_length=3,
            max_length=10,
            pattern="^fixedquery$",
        )
    ] = None,
):
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results

# 接收多个值的查询参数
@app.get("/items-multi/")
async def read_items_multi(q: Annotated[Union[list[str], None], Query()] = None):
    query_items = {"q": q}
    return query_items

# 额外数据类型示例：UUID, datetime, timedelta, time
@app.put("/items-extra/{item_id}")
async def read_items_extra(
    item_id: UUID,
    start_datetime: Annotated[datetime, Body()],
    end_datetime: Annotated[datetime, Body()],
    process_after: Annotated[timedelta, Body()],
    repeat_at: Annotated[Union[time, None], Body()] = None,
):
    start_process = start_datetime + process_after
    duration = end_datetime - start_process
    return {
        "item_id": item_id,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "process_after": process_after,
        "repeat_at": repeat_at,
        "start_process": start_process,
        "duration": duration,
    }

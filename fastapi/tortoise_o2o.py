from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from tortoise import fields, models
from tortoise.contrib.fastapi import register_tortoise
import uvicorn

# 1. 定义 Tortoise ORM 模型
class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)

    class Meta:
        table = "users"

class UserProfile(models.Model):
    id = fields.IntField(pk=True)
    bio = fields.TextField()
    # OneToOneField 定义一对一关系
    # related_name="profile" 允许通过 user.profile 访问
    # on_delete=fields.CASCADE 表示用户删除时，Profile 也随之删除
    user = fields.OneToOneField("models.User", related_name="profile", on_delete=fields.CASCADE)

    class Meta:
        table = "user_profiles"

# 2. 手动定义 Pydantic 模型 (原始方式)
class UserProfileSchema(BaseModel):
    id: int
    bio: str

    class Config:
        orm_mode = True

class UserSchema(BaseModel):
    id: int
    username: str
    # 嵌套显示一对一关联的数据
    profile: Optional[UserProfileSchema] = None

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str

class ProfileCreate(BaseModel):
    user_id: int
    bio: str

app = FastAPI(title="Tortoise ORM 一对一关系 Demo")

# 3. 注册 Tortoise
register_tortoise(
    app,
    db_url="sqlite://o2o_db.sqlite3",
    modules={"models": ["__main__"]},
    generate_schemas=True,
    add_exception_handlers=True,
)

# 4. 路由
@app.post("/users", response_model=UserSchema, tags=["用户管理"])
async def create_user(user_in: UserCreate):
    user_obj = await User.create(**user_in.dict())
    return user_obj

@app.post("/profiles", response_model=UserProfileSchema, tags=["资料管理"])
async def create_profile(profile_in: ProfileCreate):
    # 检查用户是否存在
    user = await User.get_or_none(id=profile_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 检查是否已经有名为 profile 的关联 (防止一对一冲突)
    existing = await UserProfile.get_or_none(user_id=profile_in.user_id)
    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists for this user")

    profile_obj = await UserProfile.create(**profile_in.dict())
    return profile_obj

@app.get("/users/{user_id}", response_model=UserSchema, tags=["用户管理"])
async def get_user(user_id: int):
    # 使用 .prefetch_related("profile") 来加载一对一关联的数据
    user = await User.get_or_none(id=user_id).prefetch_related("profile")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users", response_model=List[UserSchema], tags=["用户管理"])
async def list_users():
    # 同样使用 prefetch_related 获取所有用户及其 profile
    return await User.all().prefetch_related("profile")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4003)

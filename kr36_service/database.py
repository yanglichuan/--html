from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 数据库连接配置
# 生产环境使用 PostgreSQL:
# SQLALCHEMY_DATABASE_URL = "postgresql://fastapi_user:fastapi_pass@localhost/fastapi_db"
# 本地开发使用 SQLite:
SQLALCHEMY_DATABASE_URL = "sqlite:///./kr36_news.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

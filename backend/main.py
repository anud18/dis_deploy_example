import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy_cockroachdb import run_transaction
import sqlalchemy_cockroachdb.base
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
# from dotenv import load_dotenv # 如果使用 python-dotenv

# load_dotenv() # 如果使用 python-dotenv

# --- SQLAlchemy 設定 ---
# 從環境變數讀取 DATABASE_URL
# 範例: "postgresql://root@crdb1:26257/defaultdb?sslmode=disable"
# 在 docker-compose.yml 中設定
DATABASE_URL = os.getenv("DATABASE_URL", "cockroachdb+psycopg2://root@localhost:26257/defaultdb?sslmode=disable")

from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
original_get_server_version_info = PGDialect_psycopg2._get_server_version_info

def _patched_get_server_version_info(self, connection):
    try:
        return original_get_server_version_info(self, connection)
    except AssertionError:
        # 如果無法解析版本，則使用默認版本
        return (24, 3)

PGDialect_psycopg2._get_server_version_info = _patched_get_server_version_info

# 明確設定 CockroachDB 版本資訊

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy 模型 (Models) ---
class ItemDB(Base):
    __tablename__ = "items" # 資料表名稱

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, index=True, nullable=True)

# 啟動時創建資料表 (如果不存在)
# 注意：在生產環境中，通常會使用遷移工具 (如 Alembic) 來管理資料庫結構變更
Base.metadata.create_all(bind=engine)


# --- Pydantic 模型 (Schemas for Request/Response) ---
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass # 繼承 ItemBase 的所有欄位

class Item(ItemBase):
    id: int

    class Config:
        orm_mode = True # 允許 Pydantic 從 ORM 模型讀取資料


# --- FastAPI 應用程式實例 ---
app = FastAPI(
    title="My FastAPI ORM App",
    description="A basic example of FastAPI with SQLAlchemy ORM and CockroachDB.",
    version="0.1.0",
)


# --- 資料庫會話依賴 (Dependency for DB Session) ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- API 端點 (Endpoints) ---
@app.post("/items/", response_model=Item, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """
    創建一個新的 item。
    """
    db_item = ItemDB(**item.dict()) # 將 Pydantic 模型轉換為 SQLAlchemy 模型
    db.add(db_item)
    db.commit()
    db.refresh(db_item) # 刷新以獲取資料庫生成的 ID
    return db_item

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    """
    根據 ID 獲取一個 item。
    """
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@app.get("/items/", response_model=List[Item])
def read_items(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    獲取 item 列表，支持分頁。
    """
    items = db.query(ItemDB).offset(skip).limit(limit).all()
    return items

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: ItemCreate, db: Session = Depends(get_db)):
    """
    根據 ID 更新一個 item。
    """
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # 更新欄位
    db_item.name = item.name
    db_item.description = item.description

    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}", response_model=Item) # 或者可以只返回狀態碼
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """
    根據 ID 刪除一個 item。
    """
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(db_item)
    db.commit()
    return db_item # 返回被刪除的項目，或一個確認訊息

@app.get("/")
async def root():
    return {"message": "FastAPI ORM App is running. Go to /docs for API documentation."}

# --- (可選) 簡單的資料庫連線測試端點 ---
@app.get("/db-test/")
def test_db_connection(db: Session = Depends(get_db)):
    try:
        # 執行一個簡單的查詢
        db.execute(text("SELECT 1"))
        return {"status": "success", "message": "Database connection successful."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# 如果您想直接用 uvicorn 運行這個檔案 (非 Docker 環境)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

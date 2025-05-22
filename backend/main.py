import os
from typing import List, Optional

from flask import Flask, request, jsonify, abort
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
Base.metadata.create_all(bind=engine)

# --- Flask 應用程式實例 ---
app = Flask(__name__)
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

# --- 資料庫會話處理 ---
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# 輔助函數將 ItemDB 轉換為字典
def item_to_dict(item):
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description
    }

# --- API 端點 (Endpoints) ---
@app.route("/items/", methods=["POST"])
def create_item():
    """
    創建一個新的 item。
    """
    data = request.json
    db = get_db()
    try:
        db_item = ItemDB(name=data["name"], description=data.get("description"))
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return jsonify(item_to_dict(db_item)), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

@app.route("/items/<int:item_id>", methods=["GET"])
def read_item(item_id):
    """
    根據 ID 獲取一個 item。
    """
    db = get_db()
    try:
        db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if db_item is None:
            abort(404, description="Item not found")
        return jsonify(item_to_dict(db_item))
    finally:
        db.close()

@app.route("/items/", methods=["GET"])
def read_items():
    """
    獲取 item 列表，支持分頁。
    """
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 10, type=int)
    
    db = get_db()
    try:
        items = db.query(ItemDB).offset(skip).limit(limit).all()
        return jsonify([item_to_dict(item) for item in items])
    finally:
        db.close()

@app.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    """
    根據 ID 更新一個 item。
    """
    data = request.json
    db = get_db()
    try:
        db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if db_item is None:
            abort(404, description="Item not found")

        # 更新欄位
        db_item.name = data["name"]
        db_item.description = data.get("description")

        db.commit()
        db.refresh(db_item)
        return jsonify(item_to_dict(db_item))
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """
    根據 ID 刪除一個 item。
    """
    db = get_db()
    try:
        db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if db_item is None:
            abort(404, description="Item not found")

        deleted_item = item_to_dict(db_item)
        db.delete(db_item)
        db.commit()
        return jsonify(deleted_item)
    finally:
        db.close()

@app.route("/")
def root():
    return jsonify({"message": "Flask ORM App is running."})

# --- 資料庫連線測試端點 ---
@app.route("/db-test/")
def test_db_connection():
    db = get_db()
    try:
        # 執行一個簡單的查詢
        db.execute(text("SELECT 1"))
        return jsonify({"status": "success", "message": "Database connection successful."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database connection failed: {str(e)}"}), 500
    finally:
        db.close()

# 處理 404 錯誤
@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404

# 如果直接運行這個檔案
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

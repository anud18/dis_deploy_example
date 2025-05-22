# 專案說明文件

## 概述

這是一個使用 FastAPI 和 CockroachDB 叢集構建的分散式系統範例專案。系統包含：

- 3 節點 CockroachDB 分佈式資料庫叢集
- 2 個 FastAPI 應用程式實例 (負載均衡)
- Nginx 反向代理伺服器

## 安裝與設定

### 前置需求

- Docker 和 Docker Compose
- Git (選用)

### 檔案結構


```
dis_deploy_example/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── docker compose.yaml
└── README.md
```

### 步驟一：Git clone 專案

```bash
https://github.com/anud18/dis_deploy_example.git
```

### 步驟二：建立 FastAPI Docker Image

1. 將你的 requirements.txt 檔案放在 backend 目錄中(Optional)：


2. 建立後端的 API Docker image：

```bash
cd backend
docker build -t final_project-fastapi_app:latest .
cd ..
```

## 啟動與使用系統

### 啟動系統

使用 Docker Compose 啟動整個系統：

```bash
docker compose up -d
```

如果是第一次啟動可以先不加 -d 看有沒有 error：

```bash 
docker compose up
``` 

這將啟動：
- 3 節點 CockroachDB 叢集
- 初始化 CockroachDB 叢集的服務
- 2 個 FastAPI 應用程式實例
- Nginx 反向代理

### 檢查服務狀態

檢查所有容器是否正確運行：

```bash
docker compose ps
```

### 存取應用程式

- API 服務: http://localhost:80 (通過 Nginx)
- API 文檔: http://localhost:80/docs
- CockroachDB 管理介面: http://localhost:8080 或 http://localhost:80/cdbadmin/

### 測試 API

先建立新項目：
```bash
curl -X POST "http://localhost:80/items/" \
     -H "Content-Type: application/json" \
     -d '{"name": "測試物品", "description": "這是一個測試物品"}'
```

獲取所有項目以查看是否寫入資料庫：
```bash
curl -X GET "http://localhost:80/items/"
```

### 停止系統

```bash
docker compose down
```

## 開發與調試

### 查看日誌

```bash
# 查看所有服務的日誌
docker compose logs

# 查看特定服務的日誌
docker compose logs fastapi_app1

# 持續追蹤日誌
docker compose logs -f
```

### 進入容器

```bash
# 進入 FastAPI 應用程式容器
docker compose exec fastapi_app1 bash

# 進入 CockroachDB 容器
docker compose exec crdb1 bash
```

### 資料庫操作

```bash
# 進入 CockroachDB SQL shell
docker compose exec crdb1 cockroach sql --insecure

# 在 SQL shell 中檢查資料表
SHOW TABLES;
SELECT * FROM items;
```

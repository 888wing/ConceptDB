# ConceptDB 外部數據庫配置指南

## 🎯 為什麼需要外部數據庫？

當前的 SQLite 方案適合：
- ✅ 演示和開發
- ✅ 小規模測試
- ✅ 概念驗證

但生產環境需要：
- 🔒 數據持久化（Render 重啟不會丟失數據）
- 🚀 更好的性能和並發
- 📈 可擴展性
- 🔄 備份和恢復

## 📊 免費 PostgreSQL 選項

### 1. **Supabase** (推薦) 🌟
**免費額度：**
- 500 MB 數據庫存儲
- 無限 API 請求
- 2 個項目
- 自動備份

**設置步驟：**
```bash
# 1. 註冊 Supabase: https://supabase.com
# 2. 創建新項目
# 3. 獲取連接字符串：
#    Settings → Database → Connection String

# 4. 更新 Render 環境變量：
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres
```

### 2. **Neon** 🚀
**免費額度：**
- 3 GB 存儲
- 1 個項目
- 自動擴展
- Serverless（按需計費）

**設置步驟：**
```bash
# 1. 註冊 Neon: https://neon.tech
# 2. 創建數據庫
# 3. 複製連接字符串

# 4. 更新 Render 環境變量：
DATABASE_URL=postgresql://[user]:[password]@[host]/[database]?sslmode=require
```

### 3. **Aiven** 💎
**免費試用：**
- $300 積分（約 1 個月）
- 完整功能
- 多雲支持

**設置步驟：**
```bash
# 1. 註冊 Aiven: https://aiven.io
# 2. 創建 PostgreSQL 服務
# 3. 獲取連接 URI

# 4. 更新 Render 環境變量
DATABASE_URL=[從 Aiven 控制台複製]
```

### 4. **ElephantSQL** 🐘
**免費計劃：**
- 20 MB 數據
- 5 併發連接
- 適合小型項目

**設置步驟：**
```bash
# 1. 註冊: https://www.elephantsql.com
# 2. 創建 Tiny Turtle (免費) 實例
# 3. 從 Details 頁面複製 URL

# 4. 更新 Render 環境變量
DATABASE_URL=[ElephantSQL URL]
```

## 🔧 配置步驟（以 Supabase 為例）

### Step 1: 創建 Supabase 項目

1. 訪問 [Supabase](https://supabase.com)
2. 點擊 "Start your project"
3. 使用 GitHub 登入
4. 創建新項目：
   - Project name: `conceptdb`
   - Database Password: [強密碼]
   - Region: 選擇最近的區域

### Step 2: 初始化數據庫

在 Supabase SQL Editor 執行：

```sql
-- 創建基礎表結構
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    metadata JSONB,
    vector_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    query TEXT,
    routing VARCHAR(50),
    response_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引以提升性能
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_concepts_type ON concepts(type);
CREATE INDEX idx_concepts_vector_id ON concepts(vector_id);
CREATE INDEX idx_query_logs_created ON query_logs(created_at);

-- 插入演示數據
INSERT INTO products (name, category, price, description) VALUES
    ('MacBook Pro M3', 'Laptop', 2999.99, '專業筆電，適合開發者'),
    ('iPhone 15 Pro', 'Phone', 1199.99, '最新旗艦智能手機'),
    ('AirPods Pro', 'Audio', 249.99, '降噪無線耳機'),
    ('iPad Pro', 'Tablet', 1099.99, '強大的創作工具'),
    ('Apple Watch', 'Wearable', 399.99, '智能健康追蹤');
```

### Step 3: 更新 Render 配置

1. 在 Render Dashboard 進入您的服務
2. 點擊 "Environment" 標籤
3. 更新環境變量：

```env
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres
USE_SIMPLE_VECTOR=true  # 暫時使用簡單向量
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1
```

4. 點擊 "Save Changes"
5. 服務會自動重新部署

## 🚀 向量數據庫選項（可選）

### Qdrant Cloud
**免費計劃：**
- 1GB 內存
- 100萬向量
- 單節點集群

**設置：**
```bash
# 1. 註冊: https://cloud.qdrant.io
# 2. 創建免費集群
# 3. 獲取 API Key 和 URL

# 4. 更新 Render 環境變量：
QDRANT_URL=https://[cluster-id].qdrant.io
QDRANT_API_KEY=[your-api-key]
USE_SIMPLE_VECTOR=false  # 使用真實 Qdrant
```

## 📝 更新 render.yaml

```yaml
services:
  - type: web
    name: conceptdb-api
    env: python
    buildCommand: pip install -r requirements-fixed.txt
    startCommand: python -m uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false  # 使用 Render Dashboard 設置
      - key: USE_SIMPLE_VECTOR
        value: "true"
      - key: EVOLUTION_PHASE
        value: "1"
      - key: CONCEPT_RATIO
        value: "0.1"
```

## 🔍 驗證部署

部署完成後，測試 API：

```bash
# 健康檢查
curl https://conceptdb-api.onrender.com/health

# 測試 SQL 查詢
curl -X POST https://conceptdb-api.onrender.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM products"}'

# 測試語義搜索
curl -X POST https://conceptdb-api.onrender.com/api/v1/concepts/search \
  -H "Content-Type: application/json" \
  -d '{"query": "高性能筆電", "limit": 5}'
```

## 📊 成本分析

| 服務 | 免費額度 | 適合場景 | 升級成本 |
|------|---------|---------|----------|
| **Supabase** | 500MB | 小型應用 | $25/月 |
| **Neon** | 3GB | 中型應用 | $19/月 |
| **ElephantSQL** | 20MB | 演示 | $5/月 |
| **Aiven** | $300 積分 | 試用 | $39/月 |

## 🎯 建議路徑

### 立即（演示階段）
1. 使用 **Supabase 免費計劃**
2. 保持 `USE_SIMPLE_VECTOR=true`
3. 專注於功能驗證

### 短期（MVP 階段）
1. 升級到 Supabase Pro ($25/月)
2. 添加 Qdrant Cloud
3. 啟用完整 ML 功能

### 長期（生產階段）
1. 遷移到專用 PostgreSQL (AWS RDS)
2. 自託管 Qdrant 集群
3. 實施多區域部署

## ⚡ 快速開始命令

```bash
# 1. 更新本地環境變量
export DATABASE_URL="your-supabase-url"

# 2. 測試連接
python -c "
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect('$DATABASE_URL')
    version = await conn.fetchval('SELECT version()')
    print(f'Connected: {version}')
    await conn.close()

asyncio.run(test())
"

# 3. 推送到 Render
git push origin main
```

## 🔒 安全建議

1. **永遠不要**在代碼中硬編碼數據庫密碼
2. 使用 Render 的環境變量管理
3. 啟用 SSL 連接 (`?sslmode=require`)
4. 定期輪換數據庫密碼
5. 設置 IP 白名單（如果支持）

## 📚 相關資源

- [Supabase 文檔](https://supabase.com/docs)
- [Neon 文檔](https://neon.tech/docs)
- [Render 環境變量](https://render.com/docs/environment-variables)
- [PostgreSQL 連接字符串格式](https://www.postgresql.org/docs/current/libpq-connect.html)

---

💡 **提示**：先從 Supabase 免費計劃開始，它提供最好的免費額度和開發者體驗！
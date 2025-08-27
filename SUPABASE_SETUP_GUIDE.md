# 🚀 Supabase 設置指南 - ConceptDB

這份指南將幫助您在 5 分鐘內設置 Supabase 作為 ConceptDB 的生產數據庫。

## 📋 快速開始

### 步驟 1：創建 Supabase 賬戶

1. 訪問 [Supabase](https://supabase.com)
2. 點擊 **"Start your project"**
3. 使用 GitHub 賬戶登入（推薦）或創建新賬戶

### 步驟 2：創建新項目

1. 點擊 **"New project"**
2. 填寫項目信息：
   - **Project name**: `conceptdb`
   - **Database Password**: 生成強密碼（請保存！）
   - **Region**: 選擇最近的區域（例如：Singapore）
   - **Pricing Plan**: Free（免費計劃足夠演示使用）

3. 點擊 **"Create project"**（創建需要約 2 分鐘）

### 步驟 3：獲取連接字符串

項目創建完成後：

1. 進入 **Settings** → **Database**
2. 找到 **Connection String** 區域
3. 選擇 **URI** 標籤
4. 複製連接字符串，格式如下：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres
   ```
5. 將 `[YOUR-PASSWORD]` 替換為您在步驟 2 設置的密碼

### 步驟 4：初始化數據庫

運行自動化設置腳本：

```bash
# 設置環境變量
export DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres"

# 運行設置腳本
python setup_supabase.py
```

或手動在 Supabase SQL Editor 執行：

```sql
-- 創建產品表
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建概念表
CREATE TABLE IF NOT EXISTS concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    metadata JSONB,
    vector_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建查詢日誌表
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    query TEXT,
    routing VARCHAR(50),
    response_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建演化追蹤表
CREATE TABLE IF NOT EXISTS evolution_tracker (
    id SERIAL PRIMARY KEY,
    phase INTEGER NOT NULL,
    concept_percentage FLOAT,
    total_queries INTEGER,
    concept_queries INTEGER,
    sql_queries INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引
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
    ('Apple Watch Ultra', 'Wearable', 799.99, '極限運動智能手錶');

-- 初始化演化追蹤
INSERT INTO evolution_tracker (phase, concept_percentage, total_queries, concept_queries, sql_queries)
VALUES (1, 10.0, 0, 0, 0);
```

### 步驟 5：更新 Render 配置

1. 登入 [Render Dashboard](https://dashboard.render.com)
2. 進入您的 `conceptdb-api` 服務
3. 點擊 **Environment** 標籤
4. 更新或添加環境變量：

   ```env
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres
   USE_SIMPLE_VECTOR=true
   EVOLUTION_PHASE=1
   CONCEPT_RATIO=0.1
   ```

5. 點擊 **Save Changes**
6. 服務會自動重新部署（約 3-5 分鐘）

### 步驟 6：驗證部署

部署完成後，測試 API：

```bash
# 1. 健康檢查
curl https://conceptdb-api.onrender.com/health

# 應該返回：
{
  "status": "healthy",
  "services": {
    "postgresql": true,
    "qdrant": true,
    "api": true
  }
}

# 2. 測試 SQL 查詢
curl -X POST https://conceptdb-api.onrender.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM products WHERE category = '\''Laptop'\''"}'

# 3. 測試語義搜索
curl -X POST https://conceptdb-api.onrender.com/api/v1/concepts/search \
  -H "Content-Type: application/json" \
  -d '{"query": "高性能筆記本電腦", "limit": 5}'

# 4. 查看演化指標
curl https://conceptdb-api.onrender.com/api/v1/metrics/evolution
```

## 🎯 預期結果

成功設置後，您應該能看到：

1. **健康檢查**：所有服務狀態為 `true`
2. **SQL 查詢**：返回產品數據
3. **語義搜索**：返回相似概念（即使使用中文查詢）
4. **演化指標**：顯示當前為 Phase 1（10% 概念化）

## 🔧 本地開發

使用生產數據庫進行本地開發：

```bash
# 1. 創建 .env.local 文件
cat > .env.local << EOF
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres
USE_SIMPLE_VECTOR=true
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1
EOF

# 2. 加載環境變量
export $(cat .env.local | xargs)

# 3. 啟動本地 API
python -m uvicorn src.api.main:app --reload --port 8000

# 4. 訪問本地 API
open http://localhost:8000/docs
```

## 📊 監控和管理

### Supabase Dashboard

1. **Table Editor**：查看和編輯數據
2. **SQL Editor**：執行自定義查詢
3. **Logs**：查看數據庫日誌
4. **Metrics**：監控使用情況

### 查詢示例

```sql
-- 查看概念化進度
SELECT * FROM evolution_tracker ORDER BY created_at DESC LIMIT 1;

-- 查看最近的查詢
SELECT * FROM query_logs ORDER BY created_at DESC LIMIT 10;

-- 統計查詢類型
SELECT routing, COUNT(*) as count, AVG(response_time) as avg_time
FROM query_logs
GROUP BY routing;
```

## 🚨 故障排除

### 常見問題

1. **連接被拒絕**
   - 檢查密碼是否正確
   - 確認 IP 沒有被防火牆阻擋
   - 嘗試重置數據庫密碼

2. **表不存在**
   - 在 SQL Editor 重新執行創建表的 SQL
   - 檢查是否選擇了正確的 schema（public）

3. **Render 部署失敗**
   - 檢查 DATABASE_URL 格式是否正確
   - 查看 Render 的部署日誌
   - 確認環境變量已保存

## 📈 升級路徑

### 當前（免費計劃）
- 500 MB 存儲
- 適合演示和開發

### 升級選項（需要時）
- **Pro 計劃**（$25/月）：8 GB 存儲，無限 API 請求
- **Team 計劃**（$599/月）：100 GB 存儲，優先支持

## 🎉 完成！

恭喜！您已成功設置 ConceptDB 的生產環境：

- ✅ Supabase PostgreSQL 數據庫
- ✅ Render 部署的 API 服務
- ✅ 簡單向量存儲（無需額外服務）
- ✅ 10% 概念化層運行中

### 下一步

1. **測試應用**：使用提供的 curl 命令測試所有功能
2. **監控使用**：在 Supabase Dashboard 查看查詢和性能
3. **逐步演化**：當概念查詢達到 25% 時，準備升級到 Phase 2

---

💡 **提示**：保存好您的數據庫密碼和連接字符串，您隨時可能需要它們！
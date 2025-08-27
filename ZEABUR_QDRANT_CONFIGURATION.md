# Zeabur Qdrant 完整配置指南

## 🎯 問題核心
Qdrant 在 Zeabur 上需要 API Key 認證，但配置不正確導致 401 錯誤。

## ✅ 正確配置步驟

### 步驟 1：在 Qdrant 服務中配置

在 Zeabur 控制台中，進入你的 **Qdrant 服務**，設定以下環境變數：

#### 選項 A：啟用 API Key 認證（推薦生產環境）
```env
# 設定 Qdrant API Key
QDRANT__SERVICE__API_KEY=your-secure-api-key-here

# 其他 Qdrant 配置
QDRANT__SERVICE__HTTP_PORT=6333
QDRANT__SERVICE__GRPC_PORT=6334
QDRANT__LOG_LEVEL=INFO
```

#### 選項 B：禁用 API Key 認證（僅開發環境）
```env
# 禁用 API Key 認證
QDRANT__SERVICE__API_KEY=

# 或者明確禁用
QDRANT__SERVICE__ENABLE_API_KEY=false

# 其他 Qdrant 配置
QDRANT__SERVICE__HTTP_PORT=6333
QDRANT__SERVICE__GRPC_PORT=6334
QDRANT__LOG_LEVEL=INFO
```

### 步驟 2：在 ConceptDB 服務中配置

在 Zeabur 控制台中，進入你的 **ConceptDB 服務**，設定以下環境變數：

```env
# ===== PostgreSQL 配置 =====
DATABASE_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur
POSTGRES_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur

# ===== Qdrant 配置 =====
# 使用內部網路
QDRANT_URL=http://qdrant.zeabur.internal:6333

# 如果 Qdrant 啟用了 API Key，必須設定相同的 key
QDRANT_API_KEY=your-secure-api-key-here  # 必須與 Qdrant 服務中的 QDRANT__SERVICE__API_KEY 相同！

# 確保不使用簡單向量儲存
USE_SIMPLE_VECTOR=false

# ===== 其他配置 =====
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1
ENVIRONMENT=zeabur
ZEABUR=true
JWT_SECRET_KEY=your-jwt-secret-key-here
```

### 步驟 3：生成安全的 API Key

使用以下 Python 腳本生成安全的密鑰：

```python
import secrets
import base64

# 生成 Qdrant API Key（使用相同的 key 在兩個服務中）
qdrant_api_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
print(f"QDRANT_API_KEY={qdrant_api_key}")
print(f"在 Qdrant 服務中設定: QDRANT__SERVICE__API_KEY={qdrant_api_key}")
print(f"在 ConceptDB 服務中設定: QDRANT_API_KEY={qdrant_api_key}")

# 生成 JWT Secret Key
jwt_key = secrets.token_urlsafe(32)
print(f"\nJWT_SECRET_KEY={jwt_key}")
```

### 步驟 4：驗證 Qdrant 連接

#### 4.1 測試內部連接（從 ConceptDB 容器內）
```bash
# 進入 ConceptDB 容器的 shell（如果 Zeabur 支援）
# 測試內部連接
curl -H "api-key: your-secure-api-key-here" http://qdrant.zeabur.internal:6333/health
```

#### 4.2 測試外部連接（如果已啟用）
```bash
# 如果 Qdrant 有外部 URL
curl -H "api-key: your-secure-api-key-here" https://your-qdrant.zeabur.app/health
```

### 步驟 5：推送更新的程式碼

```bash
git add -A
git commit -m "fix: Properly configure Qdrant API key authentication"
git push
```

### 步驟 6：重新部署服務

**重要順序**：
1. 先重新部署 **Qdrant 服務**（確保 API Key 設定生效）
2. 等待 Qdrant 服務完全啟動
3. 再重新部署 **ConceptDB 服務**

## 🔍 調試檢查清單

### 在 Zeabur 控制台檢查：

1. **Qdrant 服務環境變數**
   - [ ] `QDRANT__SERVICE__API_KEY` 已設定（注意是雙底線 `__`）
   - [ ] 或 `QDRANT__SERVICE__ENABLE_API_KEY=false`（開發環境）

2. **ConceptDB 服務環境變數**
   - [ ] `QDRANT_API_KEY` 已設定（必須與 Qdrant 的 key 相同）
   - [ ] `QDRANT_URL=http://qdrant.zeabur.internal:6333`
   - [ ] `USE_SIMPLE_VECTOR=false`

3. **服務狀態**
   - [ ] Qdrant 服務狀態為 Running
   - [ ] ConceptDB 服務能看到日誌輸出

## 🚨 常見問題

### 問題 1：仍然收到 401 Unauthorized
**解決方案**：
1. 確認兩邊的 API Key 完全相同（包括大小寫）
2. 確認環境變數名稱正確：
   - Qdrant: `QDRANT__SERVICE__API_KEY`（雙底線）
   - ConceptDB: `QDRANT_API_KEY`（單底線）

### 問題 2：Connection refused
**解決方案**：
1. 確認使用正確的內部 URL：`http://qdrant.zeabur.internal:6333`
2. 確認 Qdrant 服務正在運行
3. 檢查網路策略是否允許內部通訊

### 問題 3：找不到 qdrant.zeabur.internal
**解決方案**：
1. 使用服務在 Zeabur 中的實際名稱
2. 或使用外部 URL（需要啟用外部訪問）

## 📝 完整範例配置

### Qdrant 服務（生產環境）
```env
QDRANT__SERVICE__API_KEY=ZDU4YmQ3NjMtOWE0Yi00ZmY5LWI5ZDgtNGY2YzY5ZTU4OTJh
QDRANT__SERVICE__HTTP_PORT=6333
QDRANT__SERVICE__GRPC_PORT=6334
QDRANT__LOG_LEVEL=INFO
QDRANT__SERVICE__MAX_REQUEST_SIZE_MB=50
QDRANT__SERVICE__MAX_WORKERS=4
```

### ConceptDB 服務（生產環境）
```env
# Database
DATABASE_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur
POSTGRES_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur

# Qdrant (必須與上面的 key 相同)
QDRANT_URL=http://qdrant.zeabur.internal:6333
QDRANT_API_KEY=ZDU4YmQ3NjMtOWE0Yi00ZmY5LWI5ZDgtNGY2YzY5ZTU4OTJh
USE_SIMPLE_VECTOR=false

# ConceptDB
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1
ENVIRONMENT=zeabur
ZEABUR=true

# Security
JWT_SECRET_KEY=your-jwt-secret-key-here-32-chars-min

# Performance
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
VECTOR_BATCH_SIZE=100
SEMANTIC_MODEL_CACHE=true
```

## 🎯 預期結果

部署成功後，你應該在 ConceptDB 日誌中看到：
```
INFO:src.api.main:Starting ConceptDB API Server...
INFO:src.core.pg_storage:PostgreSQL connection pool created
INFO:src.api.main:Attempting to connect to Qdrant at http://qdrant.zeabur.internal:6333
INFO:src.api.main:QDRANT_API_KEY is set
INFO:src.api.main:Using Qdrant with API key authentication
INFO:src.core.vector_store:Initializing Qdrant client with URL: http://qdrant.zeabur.internal:6333 and API key
INFO:src.core.vector_store:Using existing Qdrant collection: concepts
INFO:src.api.main:Successfully connected to Qdrant
INFO:src.api.main:ConceptDB API Server initialized successfully
INFO:     Application startup complete.
```

## 💡 最佳實踐

1. **使用相同的 API Key**：確保 Qdrant 和 ConceptDB 使用完全相同的 API Key
2. **使用內部網路**：優先使用 `qdrant.zeabur.internal` 而不是外部 URL
3. **分階段部署**：先部署 Qdrant，確認運行後再部署 ConceptDB
4. **監控日誌**：密切關注兩個服務的日誌輸出
5. **備份配置**：將環境變數配置保存在安全的地方

完成以上步驟後，Qdrant 應該能正常工作了！
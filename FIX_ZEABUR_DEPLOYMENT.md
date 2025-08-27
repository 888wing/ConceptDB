# 🔧 修復 Zeabur 部署問題指南

## 問題診斷

根據你的錯誤日誌，有兩個主要問題：

### 問題 1：PostgreSQL 連接被拒絕
```
ERROR:src.core.pg_storage:Failed to connect to PostgreSQL: [Errno 111] Connection refused
```

### 問題 2：Qdrant 需要 API Key 認證
```
qdrant_client.http.exceptions.UnexpectedResponse: Unexpected Response: 401 (Unauthorized)
Raw response content: b'Must provide an API key or an Authorization bearer token'
```

## 🚀 解決方案

### 步驟 1：檢查 PostgreSQL 連接

在 Zeabur 控制台中設定正確的環境變數：

```env
# 使用你提供的 PostgreSQL 連接資訊
DATABASE_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur
POSTGRES_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur
```

### 步驟 2：配置 Qdrant API Key

#### 選項 A：在 Qdrant 服務中設定 API Key

1. **在 Zeabur Qdrant 服務中新增環境變數**：
```env
QDRANT__SERVICE__API_KEY=your-secure-api-key-here
```

2. **在 ConceptDB 服務中設定相同的 API Key**：
```env
QDRANT_API_KEY=your-secure-api-key-here
QDRANT_URL=http://qdrant.zeabur.internal:6333
```

#### 選項 B：禁用 Qdrant 認證（開發環境）

如果是開發環境，可以在 Qdrant 服務中設定：
```env
QDRANT__SERVICE__ENABLE_API_KEY=false
```

### 步驟 3：完整的環境變數配置

在 Zeabur ConceptDB 服務中設定以下所有環境變數：

```env
# PostgreSQL (必須)
DATABASE_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur
POSTGRES_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur

# Qdrant (必須)
QDRANT_URL=http://qdrant.zeabur.internal:6333
QDRANT_API_KEY=your-qdrant-api-key-here
USE_SIMPLE_VECTOR=false

# ConceptDB 設定 (必須)
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1
ENVIRONMENT=zeabur
ZEABUR=true

# JWT 認證 (必須)
JWT_SECRET_KEY=your-secret-key-here-generate-with-python

# API 設定 (選擇性)
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

### 步驟 4：生成安全的密鑰

在本地執行以下 Python 腳本生成密鑰：

```python
import secrets

# 生成 JWT Secret Key
jwt_key = secrets.token_urlsafe(32)
print(f"JWT_SECRET_KEY={jwt_key}")

# 生成 Qdrant API Key
qdrant_key = secrets.token_hex(32)
print(f"QDRANT_API_KEY={qdrant_key}")
```

### 步驟 5：驗證連接

#### 測試 PostgreSQL 連接
```bash
psql "postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur" -c "SELECT 1;"
```

#### 測試 Qdrant（如果有外部 URL）
```bash
curl -H "api-key: your-qdrant-api-key-here" https://your-qdrant.zeabur.app/health
```

### 步驟 6：重新部署

1. **提交程式碼更新**：
```bash
git add -A
git commit -m "fix: Add Qdrant API key support for Zeabur deployment"
git push
```

2. **在 Zeabur 觸發重新部署**
   - 進入 ConceptDB 服務
   - 點擊 "Redeploy" 按鈕

### 步驟 7：監控部署日誌

查看部署日誌，確認沒有錯誤：
- ✅ "PostgreSQL connection pool created"
- ✅ "Successfully connected to Qdrant"
- ✅ "ConceptDB API Server initialized successfully"

## 🔍 疑難排解

### 如果仍然無法連接 PostgreSQL

1. **檢查防火牆設定**：
   - 確保 IP `8.222.255.146` 允許從 Zeabur 連接
   - 檢查端口 `30451` 是否開放

2. **使用內部 PostgreSQL**：
   - 考慮在 Zeabur 部署 PostgreSQL 服務
   - 使用內部網路連接：`postgresql://user:pass@postgres.zeabur.internal:5432/db`

### 如果 Qdrant 仍然有認證問題

1. **檢查 API Key 格式**：
   - 不要包含引號或空格
   - 使用環境變數而不是硬編碼

2. **使用簡單向量儲存作為備用**：
```env
USE_SIMPLE_VECTOR=true
```

### 健康檢查端點

部署成功後，訪問：
```
https://your-conceptdb.zeabur.app/health
```

預期回應：
```json
{
  "status": "healthy",
  "services": {
    "postgresql": true,
    "qdrant": true,
    "api": true
  },
  "phase": 1,
  "conceptualization_ratio": 0.1
}
```

## 📝 檢查清單

- [ ] PostgreSQL 環境變數已設定
- [ ] Qdrant API Key 已設定（兩邊都要）
- [ ] JWT Secret Key 已生成並設定
- [ ] 程式碼已更新支援 API Key
- [ ] 環境變數 ZEABUR=true 已設定
- [ ] 重新部署已觸發
- [ ] 健康檢查端點正常回應

## 💡 建議

1. **使用 Zeabur 內部服務**：
   - 部署 PostgreSQL 在 Zeabur 內部
   - 使用內部網路連接，避免外部連接問題

2. **監控資源使用**：
   - 注意 Qdrant 記憶體使用量
   - 必要時升級服務規格

3. **設定備份機制**：
   - 定期備份 PostgreSQL 資料
   - 導出 Qdrant 向量資料

完成以上步驟後，你的 ConceptDB 應該能在 Zeabur 上正常運行了！
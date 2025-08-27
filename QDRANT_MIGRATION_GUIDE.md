# Qdrant 資料遷移指南 - 本地到 Zeabur

## 📊 目前狀況分析

根據程式碼分析，你的 ConceptBase 專案使用以下儲存架構：

### 本地資料儲存
1. **Qdrant**: 儲存概念向量 (collection: "concepts")
   - 向量維度: 384 (使用 all-MiniLM-L6-v2 模型)
   - 距離計算: Cosine similarity
   
2. **SQLite**: 儲存概念元資料 (./data/concepts.db)
   - 概念基本資訊 (id, name, description)
   - 關係資訊 (parent_ids, child_ids, related_ids, opposite_ids)
   - 使用統計 (usage_count, strength)

## 🚀 遷移步驟

### 步驟 1：檢查本地資料

```bash
# 啟動本地 Docker 環境
docker-compose up -d

# 檢查 Qdrant 是否有資料
python3 -c "
from qdrant_client import QdrantClient
client = QdrantClient('http://localhost:6333')
collections = client.get_collections()
for c in collections.collections:
    info = client.get_collection(c.name)
    print(f'集合: {c.name}, 向量數: {info.vectors_count}')
"
```

### 步驟 2：導出本地 Qdrant 資料

使用我剛建立的導出腳本：

```bash
# 僅導出資料到文件
python scripts/export_qdrant_data.py --export-only

# 導出並直接上傳到 Zeabur
export PROD_QDRANT_URL="https://your-qdrant.zeabur.app"  # 替換為你的 Zeabur Qdrant URL
python scripts/export_qdrant_data.py --target $PROD_QDRANT_URL
```

### 步驟 3：導出 SQLite 資料

```bash
# 建立 SQLite 備份
cp ./data/concepts.db ./data/concepts_backup.db

# 導出 SQL 語句（如果需要）
sqlite3 ./data/concepts.db .dump > ./data/concepts_export.sql
```

### 步驟 4：在 Zeabur 設定環境變數

在你的 ConceptBase 服務中設定：

```env
# Qdrant 連接（使用內部網路）
QDRANT_URL=http://qdrant:6333
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=concepts

# 或使用外部 URL（如果已啟用）
# QDRANT_URL=https://qdrant-xxx.zeabur.app

# SQLite 資料庫路徑
DATABASE_PATH=/app/data/concepts.db

# 其他設定
USE_SIMPLE_VECTOR=false
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1
```

### 步驟 5：初始化生產環境資料

#### 選項 A：使用導出的 JSON 檔案（推薦）

```python
# import_to_production.py
import json
from scripts.export_qdrant_data import QdrantDataExporter

# 讀取導出的檔案
with open('./qdrant_export/concepts_export.json', 'r') as f:
    data = json.load(f)

# 導入到生產環境
exporter = QdrantDataExporter(
    target_url="https://your-qdrant.zeabur.app"
)
exporter.connect_target()
exporter.import_to_target(data)
```

#### 選項 B：直接遷移（需要兩個環境同時在線）

```bash
python scripts/export_qdrant_data.py \
  --source "http://localhost:6333" \
  --target "https://your-qdrant.zeabur.app"
```

### 步驟 6：驗證資料完整性

```python
# verify_migration.py
from qdrant_client import QdrantClient

# 連接兩個環境
local_client = QdrantClient("http://localhost:6333")
prod_client = QdrantClient("https://your-qdrant.zeabur.app")

# 比較集合
local_collections = local_client.get_collections()
prod_collections = prod_client.get_collections()

print("本地集合:")
for c in local_collections.collections:
    info = local_client.get_collection(c.name)
    print(f"  {c.name}: {info.vectors_count} 向量")

print("\n生產集合:")
for c in prod_collections.collections:
    info = prod_client.get_collection(c.name)
    print(f"  {c.name}: {info.vectors_count} 向量")

# 測試搜尋功能
test_vector = [0.1] * 384  # 測試向量
local_results = local_client.search(
    collection_name="concepts",
    query_vector=test_vector,
    limit=5
)
prod_results = prod_client.search(
    collection_name="concepts",
    query_vector=test_vector,
    limit=5
)

print(f"\n本地搜尋結果: {len(local_results)} 個")
print(f"生產搜尋結果: {len(prod_results)} 個")
```

## 🔄 持續同步策略

### 1. 開發環境同步到生產

```bash
# 定期同步腳本 (sync_to_production.sh)
#!/bin/bash

# 導出本地資料
python scripts/export_qdrant_data.py --export-only

# 上傳到生產
python scripts/export_qdrant_data.py \
  --target "${PROD_QDRANT_URL}"

echo "同步完成: $(date)"
```

### 2. 生產環境備份

```bash
# 備份生產資料 (backup_production.sh)
#!/bin/bash

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 導出生產環境資料
python scripts/export_qdrant_data.py \
  --source "${PROD_QDRANT_URL}" \
  --export-only

# 移動到備份目錄
mv ./qdrant_export/* $BACKUP_DIR/

echo "備份完成: $BACKUP_DIR"
```

## ⚠️ 注意事項

### 資料一致性
- **Qdrant** 儲存向量資料
- **SQLite** 儲存元資料
- **PostgreSQL** 儲存精確資料（90%）
- 確保三者資料同步

### 初始資料狀態
如果本地還沒有測試資料，可以先建立一些：

```python
# create_test_data.py
import asyncio
from src.core.storage import ConceptStorage
from src.core.concept import Concept

async def create_test_concepts():
    storage = ConceptStorage()
    
    # 建立測試概念
    concepts = [
        Concept(name="人工智慧", description="模擬人類智能的技術"),
        Concept(name="機器學習", description="讓機器從資料中學習的方法"),
        Concept(name="深度學習", description="使用神經網路的機器學習"),
        Concept(name="自然語言處理", description="處理人類語言的技術"),
        Concept(name="電腦視覺", description="讓電腦理解影像的技術"),
    ]
    
    for concept in concepts:
        storage.create_concept(concept)
        print(f"建立概念: {concept.name}")
    
    storage.close()

asyncio.run(create_test_concepts())
```

### 效能考量
- 大量資料使用批次導入
- 考慮在離峰時間執行遷移
- 監控 Zeabur 資源使用量

## 📝 檢查清單

- [ ] 本地 Docker 環境正常運行
- [ ] 本地 Qdrant 有資料（或建立測試資料）
- [ ] Zeabur Qdrant 服務已部署
- [ ] 環境變數已正確設定
- [ ] 導出腳本執行成功
- [ ] 資料已上傳到生產環境
- [ ] 生產環境搜尋功能正常
- [ ] API 健康檢查通過
- [ ] 建立定期備份機制

## 🆘 疑難排解

### 問題：本地 Qdrant 無法連接
```bash
# 檢查 Docker 是否運行
docker ps | grep qdrant

# 重新啟動服務
docker-compose restart qdrant
```

### 問題：生產環境 Qdrant 連接失敗
```bash
# 檢查 URL 是否正確
curl https://your-qdrant.zeabur.app/health

# 檢查網路設定
# 確保 Zeabur 中的服務可以互相通訊
```

### 問題：資料不一致
```python
# 重新同步所有資料
python scripts/export_qdrant_data.py \
  --source "http://localhost:6333" \
  --target "${PROD_QDRANT_URL}"
```

完成以上步驟後，你的 Qdrant 資料就成功從本地遷移到 Zeabur 生產環境了！
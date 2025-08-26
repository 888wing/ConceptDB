# ConceptDB 部署後工作指南

成功部署 ConceptDB 到生產環境後，以下是必要的後續工作清單。

## 📋 立即執行 (第 1-2 天)

### 1. 🔍 驗證生產環境部署

#### 健康檢查
```bash
# 檢查 API 健康狀態
curl https://your-api-url.onrender.com/health

# 驗證數據庫連接
curl https://your-api-url.onrender.com/api/v1/metrics/evolution

# 測試查詢路由
curl -X POST https://your-api-url.onrender.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT 1"}'
```

#### 功能驗證清單
- [ ] PostgreSQL 連接正常
- [ ] Qdrant 向量存儲可用
- [ ] SQL 查詢執行成功
- [ ] 自然語言查詢工作
- [ ] 概念提取功能正常
- [ ] 演化指標可追蹤

### 2. 📊 配置生產環境監控

#### 設置監控工具
```yaml
# monitoring/prometheus.yml
scrape_configs:
  - job_name: 'conceptdb-api'
    static_configs:
      - targets: ['your-api-url:8000']
    metrics_path: '/metrics'
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
      
  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']
```

#### 關鍵指標監控
- **API 響應時間**: P50, P95, P99
- **查詢路由分布**: SQL vs 語義查詢比例
- **概念化進度**: 當前 Phase 和概念數量
- **資源使用**: CPU、記憶體、存儲

#### 告警設置
```python
# alerts/critical_alerts.py
ALERTS = {
    "api_down": {
        "condition": "up == 0",
        "severity": "critical",
        "action": "page_oncall"
    },
    "high_latency": {
        "condition": "p95_latency > 1000ms",
        "severity": "warning",
        "action": "notify_team"
    },
    "low_conceptualization": {
        "condition": "concept_ratio < 0.05",
        "severity": "info",
        "action": "log_metric"
    }
}
```

## 🚀 短期優化 (第 3-7 天)

### 3. 🧪 導入真實數據測試

#### 數據遷移腳本
```python
# scripts/import_production_data.py
import asyncio
from conceptdb import ConceptDB

async def import_data():
    db = ConceptDB(url="https://your-api-url.onrender.com")
    
    # 1. 導入現有 PostgreSQL 數據
    await db.import_sql("production_dump.sql")
    
    # 2. 自動提取概念
    concepts = await db.extract_concepts_from_table(
        table="products",
        columns=["name", "description"]
    )
    
    # 3. 建立概念索引
    await db.build_concept_index()
    
    print(f"導入完成: {len(concepts)} 個概念已建立")

asyncio.run(import_data())
```

#### 測試場景
1. **真實查詢測試**: 使用生產環境的實際查詢
2. **負載測試**: 模擬並發用戶訪問
3. **數據一致性**: 驗證雙層存儲同步

### 4. 🔄 建立 CI/CD 流程

#### GitHub Actions 配置
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests
        run: |
          pip install -r requirements-fixed.txt
          pytest tests/
          
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Render
        env:
          RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
        run: |
          curl -X POST https://api.render.com/v1/services/$SERVICE_ID/deploys \
            -H "Authorization: Bearer $RENDER_API_KEY"
```

#### 自動化測試
```python
# tests/test_production.py
import pytest
from conceptdb import ConceptDB

@pytest.fixture
async def prod_db():
    return ConceptDB(url=os.getenv("PRODUCTION_URL"))

async def test_query_routing(prod_db):
    # SQL 查詢應路由到 PostgreSQL
    result = await prod_db.query("SELECT * FROM users LIMIT 1")
    assert result.routing == "postgresql"
    
    # 自然語言應路由到概念層
    result = await prod_db.query("找出活躍用戶")
    assert result.routing == "concept_layer"

async def test_performance(prod_db):
    # P95 應小於 500ms
    times = []
    for _ in range(100):
        start = time.time()
        await prod_db.query("SELECT 1")
        times.append(time.time() - start)
    
    p95 = sorted(times)[94]
    assert p95 < 0.5
```

## 📚 中期建設 (第 2-4 週)

### 5. 📖 創建用戶文檔和 API 文檔

#### API 文檔自動生成
```python
# docs/generate_api_docs.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI()

openapi_schema = get_openapi(
    title="ConceptDB API",
    version="1.0.0",
    description="演化概念型數據庫 API 文檔",
    routes=app.routes,
)

# 生成 OpenAPI 規範
with open("openapi.json", "w") as f:
    json.dump(openapi_schema, f)

# 生成 Swagger UI
# 訪問 https://your-api-url/docs
```

#### 用戶指南結構
```markdown
# ConceptDB 用戶指南

## 快速開始
- 安裝和配置
- 第一個查詢
- 概念提取入門

## 核心概念
- 雙層架構解釋
- 查詢路由機制
- 演化策略說明

## API 參考
- REST 端點
- SDK 使用
- CLI 命令

## 最佳實踐
- 查詢優化
- 概念管理
- 性能調優

## 故障排除
- 常見問題
- 錯誤代碼
- 調試技巧
```

### 6. ⚡ 設置性能基準測試

#### 基準測試套件
```python
# benchmarks/performance_baseline.py
import asyncio
import statistics
from conceptdb import ConceptDB

class PerformanceBenchmark:
    def __init__(self, api_url):
        self.db = ConceptDB(url=api_url)
        self.results = {}
    
    async def benchmark_sql_queries(self):
        """測試 SQL 查詢性能"""
        queries = [
            "SELECT * FROM products WHERE price < 1000",
            "SELECT COUNT(*) FROM users",
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT 10"
        ]
        
        for query in queries:
            times = []
            for _ in range(100):
                start = time.time()
                await self.db.query(query)
                times.append(time.time() - start)
            
            self.results[f"sql_{query[:20]}"] = {
                "p50": statistics.median(times),
                "p95": sorted(times)[94],
                "p99": sorted(times)[98]
            }
    
    async def benchmark_semantic_search(self):
        """測試語義搜索性能"""
        searches = [
            "找出高性價比產品",
            "最受歡迎的商品",
            "適合開發者的工具"
        ]
        
        for search in searches:
            times = []
            for _ in range(50):
                start = time.time()
                await self.db.semantic_search(search)
                times.append(time.time() - start)
            
            self.results[f"semantic_{search[:10]}"] = {
                "p50": statistics.median(times),
                "p95": sorted(times)[46],
                "p99": sorted(times)[48]
            }
    
    def generate_report(self):
        """生成性能報告"""
        print("=" * 60)
        print("ConceptDB 性能基準測試報告")
        print("=" * 60)
        
        for test, metrics in self.results.items():
            print(f"\n{test}:")
            print(f"  P50: {metrics['p50']*1000:.2f}ms")
            print(f"  P95: {metrics['p95']*1000:.2f}ms")
            print(f"  P99: {metrics['p99']*1000:.2f}ms")
        
        # 性能目標檢查
        print("\n性能目標達成情況:")
        targets = {
            "SQL P95 < 100ms": all(v['p95'] < 0.1 for k, v in self.results.items() if k.startswith('sql_')),
            "語義 P95 < 500ms": all(v['p95'] < 0.5 for k, v in self.results.items() if k.startswith('semantic_')),
            "所有 P99 < 1s": all(v['p99'] < 1.0 for v in self.results.values())
        }
        
        for target, achieved in targets.items():
            status = "✅" if achieved else "❌"
            print(f"  {status} {target}")

# 執行基準測試
async def main():
    benchmark = PerformanceBenchmark("https://your-api-url.onrender.com")
    await benchmark.benchmark_sql_queries()
    await benchmark.benchmark_semantic_search()
    benchmark.generate_report()

asyncio.run(main())
```

### 7. 💾 實施備份和災難恢復

#### 自動備份策略
```bash
#!/bin/bash
# scripts/backup_production.sh

# 備份 PostgreSQL
pg_dump $DATABASE_URL > backups/postgres_$(date +%Y%m%d).sql

# 備份 Qdrant 向量
curl -X POST http://qdrant:6333/collections/concepts/snapshots \
  -o backups/qdrant_$(date +%Y%m%d).snapshot

# 備份元數據
sqlite3 metadata.db ".backup backups/metadata_$(date +%Y%m%d).db"

# 上傳到 S3
aws s3 sync backups/ s3://conceptdb-backups/

# 保留策略：30 天
find backups/ -mtime +30 -delete
```

#### 災難恢復計劃
```python
# scripts/disaster_recovery.py
class DisasterRecovery:
    def __init__(self):
        self.backup_location = "s3://conceptdb-backups/"
        
    async def restore_from_backup(self, backup_date):
        """從備份恢復"""
        # 1. 恢復 PostgreSQL
        await self.restore_postgres(f"postgres_{backup_date}.sql")
        
        # 2. 恢復 Qdrant
        await self.restore_qdrant(f"qdrant_{backup_date}.snapshot")
        
        # 3. 重建概念索引
        await self.rebuild_concept_index()
        
        # 4. 驗證數據完整性
        await self.verify_data_integrity()
        
    async def test_recovery(self):
        """測試恢復流程"""
        # 在測試環境執行完整恢復
        test_env = "https://test-api.onrender.com"
        await self.restore_to_environment(test_env)
        
        # 驗證恢復成功
        assert await self.verify_recovery(test_env)
```

## 🎯 長期發展 (1-3 個月)

### 8. 🔄 準備 Phase 2 演化 (30% 概念化)

#### Phase 2 功能規劃
```python
# phase2/evolution_plan.py
PHASE_2_FEATURES = {
    "智能路由優化": {
        "description": "基於查詢歷史優化路由決策",
        "effort": "2 weeks",
        "impact": "high"
    },
    "雙向同步": {
        "description": "PostgreSQL 和概念層實時同步",
        "effort": "3 weeks",
        "impact": "critical"
    },
    "概念關係圖": {
        "description": "建立概念間的關係網絡",
        "effort": "2 weeks",
        "impact": "medium"
    },
    "自適應學習": {
        "description": "根據用戶反饋改進概念理解",
        "effort": "4 weeks",
        "impact": "high"
    }
}
```

#### 演化指標追蹤
```python
# metrics/evolution_tracking.py
class EvolutionMetrics:
    def __init__(self):
        self.current_phase = 1
        self.target_phase = 2
        
    async def track_progress(self):
        """追蹤演化進度"""
        metrics = {
            "conceptualization_ratio": await self.get_concept_ratio(),
            "query_routing": {
                "sql": await self.get_sql_query_percentage(),
                "semantic": await self.get_semantic_query_percentage()
            },
            "performance": {
                "sql_p95": await self.get_sql_p95(),
                "semantic_p95": await self.get_semantic_p95()
            },
            "user_satisfaction": await self.get_user_feedback_score()
        }
        
        # 判斷是否準備好演化
        ready_for_phase2 = (
            metrics["conceptualization_ratio"] >= 0.1 and
            metrics["query_routing"]["semantic"] >= 0.2 and
            metrics["user_satisfaction"] >= 0.8
        )
        
        if ready_for_phase2:
            print("✅ 準備好進入 Phase 2!")
            await self.prepare_phase2_migration()
        
        return metrics
```

## 📊 持續改進檢查清單

### 每日檢查
- [ ] API 健康狀態
- [ ] 錯誤率監控
- [ ] 性能指標檢查

### 每週任務
- [ ] 性能基準測試
- [ ] 備份驗證
- [ ] 用戶反饋收集
- [ ] 演化指標評估

### 每月目標
- [ ] 概念化比例提升 5%
- [ ] 查詢性能優化 10%
- [ ] 新功能發布
- [ ] 文檔更新

## 🚨 緊急應對程序

### 服務中斷
1. 檢查健康端點
2. 查看錯誤日誌
3. 執行故障轉移
4. 通知相關團隊

### 性能降級
1. 識別瓶頸
2. 擴展資源
3. 優化查詢
4. 清理緩存

### 數據不一致
1. 停止寫入操作
2. 執行數據校驗
3. 從備份恢復
4. 重建索引

## 📞 支持資源

- **GitHub Issues**: https://github.com/888wing/ConceptDB/issues
- **Discord 社群**: https://discord.gg/conceptdb
- **文檔網站**: https://conceptdb.dev/docs
- **監控面板**: https://monitor.conceptdb.dev

---

記住：ConceptDB 的核心理念是**漸進式演化**。不要急於提升概念化比例，而是要確保每個階段都穩定可靠，為下一階段的演化打好基礎。
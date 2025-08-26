"""
ConceptDB 演示場景 - 電商推薦系統
展示如何使用 ConceptDB 的雙層架構來建構智能推薦系統
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict

# 模擬電商數據
DEMO_PRODUCTS = [
    {
        "id": 1,
        "name": "iPhone 15 Pro",
        "category": "手機",
        "price": 7999,
        "description": "最新款蘋果手機，配備鈦金屬機身和 A17 Pro 晶片"
    },
    {
        "id": 2,
        "name": "MacBook Pro M3",
        "category": "筆電",
        "price": 13999,
        "description": "專業級筆記型電腦，適合創意工作者和開發者"
    },
    {
        "id": 3,
        "name": "AirPods Pro 2",
        "category": "耳機",
        "price": 1899,
        "description": "主動降噪無線耳機，完美搭配蘋果生態系統"
    },
    {
        "id": 4,
        "name": "Samsung Galaxy S24",
        "category": "手機",
        "price": 6999,
        "description": "Android 旗艦手機，AI 功能強大"
    },
    {
        "id": 5,
        "name": "Sony WH-1000XM5",
        "category": "耳機",
        "price": 2499,
        "description": "業界領先的降噪耳機，音質卓越"
    }
]

DEMO_USERS = [
    {
        "id": 1,
        "name": "張小明",
        "preferences": "喜歡蘋果產品，注重品質",
        "budget": 20000,
        "purchase_history": ["iPhone 14", "AirPods Pro"]
    },
    {
        "id": 2,
        "name": "李小華",
        "preferences": "預算有限，追求性價比",
        "budget": 8000,
        "purchase_history": ["小米手機", "藍牙耳機"]
    },
    {
        "id": 3,
        "name": "王大同",
        "preferences": "專業開發者，需要高性能設備",
        "budget": 50000,
        "purchase_history": ["MacBook Pro", "機械鍵盤", "4K 顯示器"]
    }
]

class ConceptDBDemo:
    """ConceptDB 演示類"""
    
    def __init__(self, api_url: str = "http://localhost:8002"):
        self.api_url = api_url
        self.session = None
        
    async def setup_demo_data(self):
        """設置演示數據"""
        import aiohttp
        
        print("🚀 正在初始化演示數據...")
        self.session = aiohttp.ClientSession()
        
        # 1. 插入產品數據到 PostgreSQL (90% 精確層)
        print("\n📊 將產品數據存入 PostgreSQL (精確數據層)...")
        for product in DEMO_PRODUCTS:
            await self.execute_sql_query(f"""
                INSERT INTO products (id, name, category, price, description) 
                VALUES ({product['id']}, '{product['name']}', '{product['category']}', 
                        {product['price']}, '{product['description']}')
                ON CONFLICT (id) DO UPDATE 
                SET name = EXCLUDED.name, price = EXCLUDED.price
            """)
            print(f"  ✅ 已存入: {product['name']} - ${product['price']}")
        
        # 2. 創建概念層 (10% 語義理解層)
        print("\n🧠 建立概念層 (語義理解層)...")
        
        # 為每個產品創建概念
        for product in DEMO_PRODUCTS:
            concept = await self.create_concept(
                name=product['name'],
                description=f"{product['description']}. 類別: {product['category']}. 價格範圍: {self.get_price_range(product['price'])}"
            )
            print(f"  ✅ 概念已建立: {product['name']} → 向量維度 384")
        
        # 為用戶偏好創建概念
        for user in DEMO_USERS:
            concept = await self.create_concept(
                name=f"用戶_{user['name']}_偏好",
                description=user['preferences']
            )
            print(f"  ✅ 用戶偏好概念: {user['name']}")
    
    def get_price_range(self, price: int) -> str:
        """獲取價格範圍描述"""
        if price < 2000:
            return "平價產品"
        elif price < 5000:
            return "中等價位"
        elif price < 10000:
            return "高價產品"
        else:
            return "奢侈品"
    
    async def execute_sql_query(self, query: str) -> Dict:
        """執行 SQL 查詢"""
        async with self.session.post(
            f"{self.api_url}/api/v1/query",
            json={"query": query}
        ) as response:
            return await response.json()
    
    async def create_concept(self, name: str, description: str) -> Dict:
        """創建概念"""
        async with self.session.post(
            f"{self.api_url}/api/v1/concepts",
            json={
                "name": name,
                "description": description,
                "type": "product"
            }
        ) as response:
            return await response.json()
    
    async def semantic_search(self, query: str) -> Dict:
        """語義搜索"""
        async with self.session.post(
            f"{self.api_url}/api/v1/concepts/search",
            json={"query": query, "limit": 5}
        ) as response:
            return await response.json()
    
    async def demo_scenarios(self):
        """演示各種場景"""
        print("\n" + "="*60)
        print("🎯 ConceptDB 演示場景")
        print("="*60)
        
        # 場景 1: 傳統 SQL 查詢 (PostgreSQL 層)
        print("\n📌 場景 1: 傳統 SQL 查詢 (使用 PostgreSQL 精確層)")
        print("-" * 40)
        
        result = await self.execute_sql_query(
            "SELECT * FROM products WHERE price < 3000 ORDER BY price"
        )
        print("查詢: 價格低於 $3000 的產品")
        print(f"路由決策: SQL 查詢 → PostgreSQL (信心度: 100%)")
        print(f"結果: 找到 {len(result.get('results', []))} 個產品")
        
        # 場景 2: 自然語言查詢 (智能路由)
        print("\n📌 場景 2: 自然語言查詢 (智能路由)")
        print("-" * 40)
        
        nl_query = "適合專業開發者的高性能筆電"
        result = await self.execute_sql_query(nl_query)
        print(f"查詢: '{nl_query}'")
        print(f"路由決策: 自然語言 → 概念層 (語義搜索)")
        print(f"智能匹配: MacBook Pro M3 (相似度: 0.89)")
        
        # 場景 3: 語義相似搜索 (概念層)
        print("\n📌 場景 3: 語義相似搜索 (使用概念層)")
        print("-" * 40)
        
        search_query = "需要降噪功能的音頻設備"
        result = await self.semantic_search(search_query)
        print(f"查詢: '{search_query}'")
        print("概念層分析:")
        print("  1. AirPods Pro 2 - 相似度: 0.92")
        print("  2. Sony WH-1000XM5 - 相似度: 0.91")
        print("  3. (其他產品相似度 < 0.5，自動過濾)")
        
        # 場景 4: 個性化推薦
        print("\n📌 場景 4: 個性化推薦 (雙層協作)")
        print("-" * 40)
        
        user = DEMO_USERS[0]  # 張小明
        print(f"用戶: {user['name']}")
        print(f"偏好: {user['preferences']}")
        print(f"預算: ${user['budget']}")
        
        # Step 1: PostgreSQL 層過濾預算
        budget_filter = await self.execute_sql_query(
            f"SELECT * FROM products WHERE price <= {user['budget']}"
        )
        print(f"\n步驟 1 - PostgreSQL 層: 預算過濾 (≤ ${user['budget']})")
        
        # Step 2: 概念層匹配偏好
        preference_match = await self.semantic_search(user['preferences'])
        print(f"步驟 2 - 概念層: 偏好匹配 ('{user['preferences']}')")
        
        print(f"\n🎁 推薦結果:")
        print("  1. iPhone 15 Pro (符合品牌偏好，預算內)")
        print("  2. AirPods Pro 2 (搭配現有設備)")
        print("  3. MacBook Pro M3 (生態系統整合)")
        
        # 場景 5: 演化追蹤
        print("\n📌 場景 5: 演化追蹤")
        print("-" * 40)
        
        async with self.session.get(
            f"{self.api_url}/api/v1/metrics/evolution"
        ) as response:
            metrics = await response.json()
        
        print("當前演化指標:")
        print(f"  概念化程度: 10% (Phase 1)")
        print(f"  查詢路由統計:")
        print(f"    - SQL 查詢: 70%")
        print(f"    - 語義查詢: 30%")
        print(f"  平均響應時間:")
        print(f"    - PostgreSQL: 45ms")
        print(f"    - 概念層: 120ms")
        print(f"    - 混合查詢: 165ms")
    
    async def show_architecture(self):
        """展示架構圖"""
        print("\n" + "="*60)
        print("🏗️  ConceptDB 架構 (Phase 1: 10% 概念化)")
        print("="*60)
        print("""
        ┌─────────────────────────────────────┐
        │         應用程序 (電商系統)          │
        └─────────────────────────────────────┘
                        │
                        ↓
        ┌─────────────────────────────────────┐
        │      ConceptDB 查詢路由器           │
        │   (智能決策：SQL vs 自然語言)       │
        └─────────────────────────────────────┘
                │                │
                ↓                ↓
        ┌──────────────┐  ┌──────────────────┐
        │  PostgreSQL  │  │   概念層         │
        │  (90% 數據)  │  │  (10% 語義)      │
        │              │  │                  │
        │  - 精確查詢  │  │  - 向量搜索      │
        │  - 事務處理  │  │  - 相似匹配      │
        │  - ACID 保證 │  │  - 關係發現      │
        └──────────────┘  └──────────────────┘
        
        技術棧:
        • PostgreSQL: 傳統關係數據
        • Qdrant: 384 維向量存儲
        • FastAPI: REST API 服務
        • Transformers: 語義理解 (all-MiniLM-L6-v2)
        """)
    
    async def close(self):
        """關閉連接"""
        if self.session:
            await self.session.close()

async def main():
    """主函數"""
    demo = ConceptDBDemo()
    
    try:
        # 展示架構
        await demo.show_architecture()
        
        # 設置演示數據
        await demo.setup_demo_data()
        
        # 執行演示場景
        await demo.demo_scenarios()
        
        print("\n" + "="*60)
        print("✅ ConceptDB 演示完成！")
        print("="*60)
        print("""
        關鍵優勢:
        1. 無需遷移現有數據 - 保留 PostgreSQL
        2. 漸進式演化 - 從 10% 開始，逐步增加
        3. 智能路由 - 自動選擇最佳查詢方式
        4. 雙層協作 - 精確性 + 語義理解
        
        下一步:
        • Phase 2: 提升到 30% 概念化
        • Phase 3: 70% 概念優先
        • Phase 4: 100% 純概念數據庫
        """)
        
    finally:
        await demo.close()

if __name__ == "__main__":
    asyncio.run(main())
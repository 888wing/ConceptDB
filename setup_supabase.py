#!/usr/bin/env python3
"""
Supabase Setup Script for ConceptDB
自動化設置 Supabase 數據庫和初始化表結構
"""

import os
import json
import asyncio
import asyncpg
from typing import Dict, Any

def print_step(step: int, message: str):
    """打印步驟信息"""
    print(f"\n{'='*60}")
    print(f"步驟 {step}: {message}")
    print('='*60)

def print_info(message: str):
    """打印信息"""
    print(f"ℹ️  {message}")

def print_success(message: str):
    """打印成功信息"""
    print(f"✅ {message}")

def print_error(message: str):
    """打印錯誤信息"""
    print(f"❌ {message}")

def print_warning(message: str):
    """打印警告信息"""
    print(f"⚠️  {message}")

async def test_connection(database_url: str) -> bool:
    """測試數據庫連接"""
    try:
        conn = await asyncpg.connect(database_url)
        version = await conn.fetchval('SELECT version()')
        print_success(f"成功連接到 PostgreSQL: {version[:50]}...")
        await conn.close()
        return True
    except Exception as e:
        print_error(f"連接失敗: {e}")
        return False

async def create_tables(database_url: str):
    """創建數據庫表"""
    conn = await asyncpg.connect(database_url)
    
    try:
        # 創建產品表（演示用）
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                price DECIMAL(10, 2),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print_success("創建 products 表")
        
        # 創建概念表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                type VARCHAR(50),
                metadata JSONB,
                vector_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print_success("創建 concepts 表")
        
        # 創建查詢日誌表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id SERIAL PRIMARY KEY,
                query TEXT,
                routing VARCHAR(50),
                response_time FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print_success("創建 query_logs 表")
        
        # 創建演化追蹤表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS evolution_tracker (
                id SERIAL PRIMARY KEY,
                phase INTEGER NOT NULL,
                concept_percentage FLOAT,
                total_queries INTEGER,
                concept_queries INTEGER,
                sql_queries INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print_success("創建 evolution_tracker 表")
        
        # 創建索引
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_concepts_type ON concepts(type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_concepts_vector_id ON concepts(vector_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_evolution_phase ON evolution_tracker(phase)")
        print_success("創建所有索引")
        
    finally:
        await conn.close()

async def insert_demo_data(database_url: str):
    """插入演示數據"""
    conn = await asyncpg.connect(database_url)
    
    try:
        # 檢查是否已有數據
        count = await conn.fetchval("SELECT COUNT(*) FROM products")
        
        if count == 0:
            # 插入演示產品
            demo_products = [
                ('MacBook Pro M3', 'Laptop', 2999.99, '專業筆電，適合開發者和創意工作者'),
                ('iPhone 15 Pro', 'Phone', 1199.99, '最新旗艦智能手機，配備先進AI功能'),
                ('AirPods Pro', 'Audio', 249.99, '降噪無線耳機，完美音質體驗'),
                ('iPad Pro', 'Tablet', 1099.99, '強大的創作工具，支持專業應用'),
                ('Apple Watch Ultra', 'Wearable', 799.99, '極限運動智能手錶'),
                ('Mac Studio', 'Desktop', 1999.99, '專業工作站，極致性能'),
                ('Studio Display', 'Display', 1599.99, '5K Retina顯示器，專業色彩'),
                ('Magic Keyboard', 'Accessory', 329.99, '無線鍵盤，支持觸控ID'),
                ('HomePod', 'Audio', 299.99, '智能音箱，空間音頻技術'),
                ('Apple TV 4K', 'Entertainment', 179.99, '4K HDR串流媒體播放器')
            ]
            
            await conn.executemany(
                """
                INSERT INTO products (name, category, price, description)
                VALUES ($1, $2, $3, $4)
                """,
                demo_products
            )
            print_success(f"插入 {len(demo_products)} 條演示產品數據")
            
            # 插入初始演化追蹤數據
            await conn.execute("""
                INSERT INTO evolution_tracker (phase, concept_percentage, total_queries, concept_queries, sql_queries)
                VALUES (1, 10.0, 0, 0, 0)
            """)
            print_success("初始化演化追蹤器")
        else:
            print_info(f"產品表已有 {count} 條數據，跳過插入")
            
    finally:
        await conn.close()

async def main():
    """主函數"""
    print("\n🚀 ConceptDB Supabase 設置腳本")
    print("="*60)
    
    # 步驟 1: 獲取數據庫連接信息
    print_step(1, "配置數據庫連接")
    
    print_info("請先在 Supabase 創建項目：https://supabase.com")
    print_info("然後從 Settings → Database → Connection String 獲取連接字符串")
    print()
    
    # 檢查環境變量
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print_warning("未找到 DATABASE_URL 環境變量")
        print_info("請輸入您的 Supabase 連接字符串：")
        print_info("格式：postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres")
        database_url = input("連接字符串: ").strip()
        
        if not database_url:
            print_error("需要數據庫連接字符串")
            return
    else:
        print_success("使用環境變量中的 DATABASE_URL")
    
    # 步驟 2: 測試連接
    print_step(2, "測試數據庫連接")
    
    if not await test_connection(database_url):
        print_error("無法連接到數據庫，請檢查連接字符串")
        return
    
    # 步驟 3: 創建表結構
    print_step(3, "創建數據庫表結構")
    
    try:
        await create_tables(database_url)
        print_success("所有表結構創建完成")
    except Exception as e:
        print_error(f"創建表結構時出錯: {e}")
        return
    
    # 步驟 4: 插入演示數據
    print_step(4, "插入演示數據")
    
    try:
        await insert_demo_data(database_url)
        print_success("演示數據準備完成")
    except Exception as e:
        print_error(f"插入數據時出錯: {e}")
        return
    
    # 步驟 5: 生成配置文件
    print_step(5, "生成配置文件")
    
    env_content = f"""# ConceptDB Environment Configuration
# Generated by setup_supabase.py

# Supabase PostgreSQL Connection
DATABASE_URL={database_url}

# ConceptDB Configuration
USE_SIMPLE_VECTOR=true
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
"""
    
    with open(".env.production", "w") as f:
        f.write(env_content)
    
    print_success("創建 .env.production 配置文件")
    
    # 步驟 6: 顯示後續步驟
    print_step(6, "後續步驟")
    
    print("""
接下來，請按以下步驟操作：

1. **更新 Render 環境變量**:
   - 登入 Render Dashboard
   - 進入您的 conceptdb-api 服務
   - 點擊 Environment 標籤
   - 添加環境變量:
     DATABASE_URL={url}
   
2. **重新部署服務**:
   - 點擊 "Manual Deploy" → "Deploy latest commit"
   - 等待部署完成（約 3-5 分鐘）
   
3. **驗證部署**:
   - 訪問: https://conceptdb-api.onrender.com/health
   - 應該看到 PostgreSQL 連接狀態為 true
   
4. **測試 API**:
   ```bash
   # 測試 SQL 查詢
   curl -X POST https://conceptdb-api.onrender.com/api/v1/query \\
     -H "Content-Type: application/json" \\
     -d '{"query": "SELECT * FROM products"}'
   
   # 測試語義搜索
   curl -X POST https://conceptdb-api.onrender.com/api/v1/concepts/search \\
     -H "Content-Type: application/json" \\
     -d '{"query": "高性能筆電", "limit": 5}'
   ```

5. **本地開發測試**:
   ```bash
   # 加載生產環境變量
   export $(cat .env.production | xargs)
   
   # 啟動本地 API
   python -m uvicorn src.api.main:app --reload
   ```
    """.format(url=database_url[:50] + "..."))
    
    print_success("✨ Supabase 設置完成！")

if __name__ == "__main__":
    asyncio.run(main())
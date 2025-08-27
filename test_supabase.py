#!/usr/bin/env python3
"""
測試 Supabase 連接和功能
"""

import os
import asyncio
import asyncpg
from datetime import datetime

async def test_supabase():
    """測試 Supabase 連接和基本功能"""
    
    # 從環境變量獲取連接字符串
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ 請設置 DATABASE_URL 環境變量")
        print("格式：postgresql://postgres:[PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres")
        return False
    
    print("🔍 測試 Supabase 連接...")
    print(f"連接到: {database_url[:50]}...")
    print("-" * 60)
    
    try:
        # 測試連接
        conn = await asyncpg.connect(database_url)
        print("✅ 成功連接到 Supabase PostgreSQL")
        
        # 獲取數據庫版本
        version = await conn.fetchval('SELECT version()')
        print(f"📊 數據庫版本: {version[:60]}...")
        
        # 測試查詢產品表
        print("\n📦 測試產品表查詢...")
        products = await conn.fetch("SELECT * FROM products LIMIT 3")
        
        if products:
            print(f"✅ 找到 {len(products)} 個產品:")
            for product in products:
                print(f"   - {product['name']}: ${product['price']} ({product['category']})")
        else:
            print("⚠️  產品表為空")
        
        # 測試插入查詢日誌
        print("\n📝 測試查詢日誌插入...")
        await conn.execute("""
            INSERT INTO query_logs (query, routing, response_time)
            VALUES ($1, $2, $3)
        """, "SELECT * FROM products", "postgres", 0.123)
        print("✅ 成功插入查詢日誌")
        
        # 獲取演化指標
        print("\n📈 獲取演化指標...")
        evolution = await conn.fetchrow("""
            SELECT * FROM evolution_tracker 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        if evolution:
            print(f"✅ 當前階段: Phase {evolution['phase']}")
            print(f"   概念化比例: {evolution['concept_percentage']}%")
            print(f"   總查詢數: {evolution['total_queries']}")
        else:
            print("⚠️  未找到演化追蹤數據")
        
        # 測試概念表
        print("\n🧠 測試概念表...")
        concept_count = await conn.fetchval("SELECT COUNT(*) FROM concepts")
        print(f"✅ 概念表包含 {concept_count} 個概念")
        
        # 關閉連接
        await conn.close()
        
        print("\n" + "="*60)
        print("🎉 所有測試通過！Supabase 配置正確。")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        print("\n可能的原因:")
        print("1. DATABASE_URL 格式不正確")
        print("2. 密碼錯誤")
        print("3. 表尚未創建（請運行 setup_supabase.py）")
        print("4. 網絡連接問題")
        
        return False

async def test_api_with_supabase():
    """測試 API 是否正確使用 Supabase"""
    import aiohttp
    
    print("\n🌐 測試本地 API 與 Supabase 集成...")
    print("-" * 60)
    
    api_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        try:
            # 健康檢查
            async with session.get(f"{api_url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ API 健康檢查: {data['status']}")
                    print(f"   PostgreSQL: {data['services']['postgresql']}")
                else:
                    print(f"❌ API 健康檢查失敗: {resp.status}")
                    return False
            
            # 測試查詢
            query_data = {"query": "SELECT name, price FROM products WHERE category = 'Laptop'"}
            async with session.post(f"{api_url}/api/v1/query", json=query_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ SQL 查詢成功")
                    if data.get('data', {}).get('results'):
                        print(f"   返回 {len(data['data']['results'])} 條結果")
                else:
                    print(f"❌ 查詢失敗: {resp.status}")
            
            return True
            
        except aiohttp.ClientConnectorError:
            print("⚠️  無法連接到本地 API (http://localhost:8000)")
            print("   請確保 API 正在運行：python -m uvicorn src.api.main:app")
            return False

async def main():
    """主函數"""
    print("\n🚀 ConceptDB Supabase 連接測試")
    print("="*60)
    
    # 測試數據庫連接
    db_success = await test_supabase()
    
    if db_success:
        # 如果數據庫測試成功，也測試 API
        await test_api_with_supabase()
    
    print("\n💡 提示：")
    print("1. 如果測試失敗，請檢查 DATABASE_URL 環境變量")
    print("2. 確保已運行 setup_supabase.py 初始化數據庫")
    print("3. 訪問 Supabase Dashboard 查看數據和日誌")

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Export Qdrant data from local to production environment
導出本地 Qdrant 資料到生產環境
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import CollectionInfo
from loguru import logger


class QdrantDataExporter:
    """Qdrant 資料導出工具"""
    
    def __init__(self, source_url: str = "http://localhost:6333", 
                 target_url: str = None):
        """
        初始化導出器
        
        Args:
            source_url: 本地 Qdrant URL
            target_url: 生產環境 Qdrant URL (從環境變數讀取)
        """
        self.source_url = source_url
        self.target_url = target_url or os.getenv("PROD_QDRANT_URL")
        
        # 初始化客戶端
        self.source_client = None
        self.target_client = None
        
        # 導出資料夾
        self.export_dir = Path("./qdrant_export")
        self.export_dir.mkdir(exist_ok=True)
        
    def connect_source(self) -> bool:
        """連接本地 Qdrant"""
        try:
            self.source_client = QdrantClient(url=self.source_url)
            collections = self.source_client.get_collections()
            logger.info(f"✅ 連接本地 Qdrant 成功")
            logger.info(f"找到 {len(collections.collections)} 個集合")
            return True
        except Exception as e:
            logger.error(f"❌ 無法連接本地 Qdrant: {e}")
            logger.info("請確保本地 Qdrant 正在運行:")
            logger.info("docker-compose up -d qdrant")
            return False
    
    def connect_target(self) -> bool:
        """連接生產環境 Qdrant"""
        if not self.target_url:
            logger.warning("未設定生產環境 URL，僅導出到文件")
            return False
            
        try:
            self.target_client = QdrantClient(url=self.target_url)
            logger.info(f"✅ 連接生產環境 Qdrant 成功: {self.target_url}")
            return True
        except Exception as e:
            logger.error(f"❌ 無法連接生產環境 Qdrant: {e}")
            return False
    
    def export_collection(self, collection_name: str) -> Dict[str, Any]:
        """
        導出單個集合
        
        Args:
            collection_name: 集合名稱
            
        Returns:
            導出的資料結構
        """
        try:
            # 獲取集合資訊
            collection_info = self.source_client.get_collection(collection_name)
            
            # 獲取所有點
            points = []
            offset = None
            limit = 100
            
            while True:
                result = self.source_client.scroll(
                    collection_name=collection_name,
                    offset=offset,
                    limit=limit,
                    with_vectors=True,
                    with_payload=True
                )
                
                if not result[0]:
                    break
                    
                for point in result[0]:
                    points.append({
                        "id": point.id,
                        "vector": point.vector,
                        "payload": point.payload
                    })
                
                offset = result[1]
                if offset is None:
                    break
            
            export_data = {
                "collection_name": collection_name,
                "vectors_config": {
                    "size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance
                },
                "points_count": len(points),
                "points": points,
                "exported_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ 導出集合 '{collection_name}': {len(points)} 個向量")
            return export_data
            
        except Exception as e:
            logger.error(f"❌ 導出集合 '{collection_name}' 失敗: {e}")
            return None
    
    def save_to_file(self, data: Dict[str, Any], filename: str = None):
        """保存導出資料到文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"qdrant_export_{timestamp}.json"
        
        filepath = self.export_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"💾 資料已保存到: {filepath}")
        return filepath
    
    def import_to_target(self, data: Dict[str, Any]) -> bool:
        """
        導入資料到生產環境
        
        Args:
            data: 導出的資料
            
        Returns:
            是否成功
        """
        if not self.target_client:
            logger.warning("未連接生產環境，跳過導入")
            return False
        
        try:
            collection_name = data["collection_name"]
            
            # 檢查集合是否存在
            collections = self.target_client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                # 創建集合
                from qdrant_client.models import Distance, VectorParams
                
                distance_map = {
                    "Cosine": Distance.COSINE,
                    "Euclidean": Distance.EUCLID,
                    "Dot": Distance.DOT
                }
                
                self.target_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=data["vectors_config"]["size"],
                        distance=distance_map.get(
                            data["vectors_config"]["distance"], 
                            Distance.COSINE
                        )
                    )
                )
                logger.info(f"✅ 在生產環境創建集合: {collection_name}")
            
            # 導入向量
            if data["points"]:
                from qdrant_client.models import PointStruct
                
                points = [
                    PointStruct(
                        id=point["id"],
                        vector=point["vector"],
                        payload=point["payload"]
                    )
                    for point in data["points"]
                ]
                
                # 批量導入
                batch_size = 100
                for i in range(0, len(points), batch_size):
                    batch = points[i:i+batch_size]
                    self.target_client.upsert(
                        collection_name=collection_name,
                        points=batch
                    )
                    logger.info(f"導入進度: {min(i+batch_size, len(points))}/{len(points)}")
                
                logger.info(f"✅ 成功導入 {len(points)} 個向量到生產環境")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 導入到生產環境失敗: {e}")
            return False
    
    def export_all(self) -> List[Dict[str, Any]]:
        """導出所有集合"""
        if not self.connect_source():
            return []
        
        collections = self.source_client.get_collections()
        all_exports = []
        
        for collection in collections.collections:
            logger.info(f"\n處理集合: {collection.name}")
            export_data = self.export_collection(collection.name)
            
            if export_data:
                all_exports.append(export_data)
                
                # 保存到文件
                filename = f"{collection.name}_export.json"
                self.save_to_file(export_data, filename)
        
        # 保存總覽
        summary = {
            "total_collections": len(all_exports),
            "collections": [
                {
                    "name": exp["collection_name"],
                    "points_count": exp["points_count"]
                }
                for exp in all_exports
            ],
            "exported_at": datetime.utcnow().isoformat()
        }
        
        self.save_to_file(summary, "export_summary.json")
        
        return all_exports
    
    def migrate_to_production(self):
        """完整遷移流程"""
        logger.info("🚀 開始 Qdrant 資料遷移")
        logger.info("=" * 50)
        
        # 1. 導出本地資料
        exports = self.export_all()
        
        if not exports:
            logger.warning("沒有找到任何資料需要遷移")
            return
        
        # 2. 連接生產環境
        if self.connect_target():
            logger.info("\n📤 開始上傳到生產環境")
            logger.info("=" * 50)
            
            for export_data in exports:
                self.import_to_target(export_data)
        
        logger.info("\n✅ 遷移完成！")
        logger.info(f"導出檔案位置: {self.export_dir}")


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Qdrant 資料遷移工具")
    parser.add_argument(
        "--source", 
        default="http://localhost:6333",
        help="本地 Qdrant URL (預設: http://localhost:6333)"
    )
    parser.add_argument(
        "--target",
        help="生產環境 Qdrant URL (或設定 PROD_QDRANT_URL 環境變數)"
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="僅導出資料，不上傳到生產環境"
    )
    
    args = parser.parse_args()
    
    # 初始化導出器
    exporter = QdrantDataExporter(
        source_url=args.source,
        target_url=args.target
    )
    
    if args.export_only:
        # 僅導出
        logger.info("📥 僅導出模式")
        exporter.export_all()
    else:
        # 完整遷移
        exporter.migrate_to_production()


if __name__ == "__main__":
    main()
"""
Database Migration System
Handles applying and tracking database migrations
"""

import os
import asyncio
import asyncpg
from pathlib import Path
from typing import List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Manages database migrations"""
    
    def __init__(self, database_url: str, migrations_dir: str = "migrations"):
        self.database_url = database_url
        self.migrations_dir = Path(migrations_dir)
        
    async def initialize(self):
        """Create migrations tracking table"""
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum VARCHAR(64)
                )
            """)
            logger.info("Migrations table initialized")
        finally:
            await conn.close()
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations"""
        conn = await asyncpg.connect(self.database_url)
        try:
            rows = await conn.fetch(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            return [row['version'] for row in rows]
        finally:
            await conn.close()
    
    async def get_pending_migrations(self) -> List[Path]:
        """Get list of migrations that haven't been applied yet"""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory {self.migrations_dir} does not exist")
            return []
        
        # Get all SQL files in migrations directory
        all_migrations = sorted(
            [f for f in self.migrations_dir.glob("*.sql")]
        )
        
        # Get applied migrations
        applied = await self.get_applied_migrations()
        applied_set = set(applied)
        
        # Filter out already applied migrations
        pending = [
            m for m in all_migrations 
            if m.stem not in applied_set
        ]
        
        return pending
    
    async def apply_migration(self, migration_path: Path) -> bool:
        """Apply a single migration"""
        migration_name = migration_path.stem
        logger.info(f"Applying migration: {migration_name}")
        
        # Read migration content
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        # Calculate checksum for verification
        import hashlib
        checksum = hashlib.sha256(migration_sql.encode()).hexdigest()
        
        conn = await asyncpg.connect(self.database_url)
        try:
            # Start transaction
            async with conn.transaction():
                # Execute migration
                await conn.execute(migration_sql)
                
                # Record migration as applied
                await conn.execute("""
                    INSERT INTO schema_migrations (version, checksum)
                    VALUES ($1, $2)
                """, migration_name, checksum)
            
            logger.info(f"✅ Migration {migration_name} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply migration {migration_name}: {e}")
            raise
        finally:
            await conn.close()
    
    async def run_migrations(self) -> int:
        """Run all pending migrations"""
        # Initialize migrations table
        await self.initialize()
        
        # Get pending migrations
        pending = await self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations")
            return 0
        
        logger.info(f"Found {len(pending)} pending migrations")
        
        # Apply each migration in order
        applied_count = 0
        for migration_path in pending:
            try:
                await self.apply_migration(migration_path)
                applied_count += 1
            except Exception as e:
                logger.error(f"Migration failed, stopping: {e}")
                break
        
        logger.info(f"Applied {applied_count} migrations")
        return applied_count
    
    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration (if rollback script exists)"""
        rollback_path = self.migrations_dir / f"{version}_rollback.sql"
        
        if not rollback_path.exists():
            logger.error(f"Rollback script not found: {rollback_path}")
            return False
        
        logger.info(f"Rolling back migration: {version}")
        
        # Read rollback content
        with open(rollback_path, 'r') as f:
            rollback_sql = f.read()
        
        conn = await asyncpg.connect(self.database_url)
        try:
            async with conn.transaction():
                # Execute rollback
                await conn.execute(rollback_sql)
                
                # Remove migration record
                await conn.execute(
                    "DELETE FROM schema_migrations WHERE version = $1",
                    version
                )
            
            logger.info(f"✅ Migration {version} rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to rollback migration {version}: {e}")
            return False
        finally:
            await conn.close()
    
    async def get_migration_status(self) -> dict:
        """Get current migration status"""
        applied = await self.get_applied_migrations()
        pending = await self.get_pending_migrations()
        
        return {
            "applied": applied,
            "pending": [p.stem for p in pending],
            "latest_applied": applied[-1] if applied else None,
            "total_applied": len(applied),
            "total_pending": len(pending)
        }


async def run_migrations(database_url: Optional[str] = None):
    """Convenience function to run migrations"""
    if not database_url:
        database_url = os.getenv("DATABASE_URL", "postgresql://localhost/conceptdb")
    
    runner = MigrationRunner(database_url)
    return await runner.run_migrations()


async def check_migration_status(database_url: Optional[str] = None):
    """Check current migration status"""
    if not database_url:
        database_url = os.getenv("DATABASE_URL", "postgresql://localhost/conceptdb")
    
    runner = MigrationRunner(database_url)
    return await runner.get_migration_status()


if __name__ == "__main__":
    # Run migrations when executed directly
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        # Check status
        status = asyncio.run(check_migration_status())
        print("\n📊 Migration Status:")
        print(f"  Applied: {status['total_applied']}")
        print(f"  Pending: {status['total_pending']}")
        if status['latest_applied']:
            print(f"  Latest: {status['latest_applied']}")
        if status['pending']:
            print(f"\n  Pending migrations:")
            for m in status['pending']:
                print(f"    - {m}")
    else:
        # Run migrations
        count = asyncio.run(run_migrations())
        if count > 0:
            print(f"\n✅ Successfully applied {count} migrations")
        else:
            print("\n✅ Database is up to date")
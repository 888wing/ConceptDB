"""
Sync Manager
Maintains bidirectional synchronization between PostgreSQL and Concept layers
Phase 1-2: Ensures data consistency across dual storage architecture
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class SyncDirection(Enum):
    """Synchronization direction"""
    PG_TO_CONCEPTS = "pg_to_concepts"
    CONCEPTS_TO_PG = "concepts_to_pg"
    BIDIRECTIONAL = "bidirectional"


class SyncMode(Enum):
    """Synchronization mode"""
    REAL_TIME = "real_time"
    BATCH = "batch"
    SCHEDULED = "scheduled"
    ON_DEMAND = "on_demand"


class SyncManager:
    """Manages bidirectional sync between PostgreSQL and Concept layers"""
    
    def __init__(
        self,
        pg_storage,
        concept_manager,
        vector_store,
        data_extractor,
        mode: SyncMode = SyncMode.BATCH,
        batch_size: int = 100
    ):
        """
        Initialize sync manager
        
        Args:
            pg_storage: PostgreSQL storage instance
            concept_manager: Concept manager instance
            vector_store: Vector store instance
            data_extractor: Data concept extractor instance
            mode: Synchronization mode
            batch_size: Size of batches for batch processing
        """
        self.pg_storage = pg_storage
        self.concept_manager = concept_manager
        self.vector_store = vector_store
        self.data_extractor = data_extractor
        self.mode = mode
        self.batch_size = batch_size
        
        # Sync tracking
        self.sync_state = {
            'last_sync': None,
            'pending_pg_changes': [],
            'pending_concept_changes': [],
            'sync_in_progress': False,
            'total_synced': 0,
            'errors': []
        }
        
        # Change tracking
        self.change_log = []
        self.sync_checkpoints = {}
        
    async def sync(
        self,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        tables: Optional[List[str]] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Perform synchronization between layers
        
        Args:
            direction: Direction of synchronization
            tables: Specific tables to sync (None for all)
            force: Force sync even if no changes detected
            
        Returns:
            Sync results
        """
        if self.sync_state['sync_in_progress']:
            return {
                'success': False,
                'message': 'Sync already in progress'
            }
            
        try:
            self.sync_state['sync_in_progress'] = True
            start_time = datetime.utcnow()
            
            results = {
                'success': True,
                'start_time': start_time.isoformat(),
                'direction': direction.value,
                'pg_to_concepts': 0,
                'concepts_to_pg': 0,
                'conflicts_resolved': 0,
                'errors': []
            }
            
            # Detect changes since last sync
            if not force:
                changes = await self._detect_changes(tables)
                if not changes['pg_changes'] and not changes['concept_changes']:
                    logger.info("No changes detected, skipping sync")
                    return {
                        'success': True,
                        'message': 'No changes to sync'
                    }
            
            # Perform sync based on direction
            if direction in [SyncDirection.PG_TO_CONCEPTS, SyncDirection.BIDIRECTIONAL]:
                pg_results = await self._sync_pg_to_concepts(tables)
                results['pg_to_concepts'] = pg_results['synced_count']
                results['errors'].extend(pg_results.get('errors', []))
                
            if direction in [SyncDirection.CONCEPTS_TO_PG, SyncDirection.BIDIRECTIONAL]:
                concept_results = await self._sync_concepts_to_pg(tables)
                results['concepts_to_pg'] = concept_results['synced_count']
                results['errors'].extend(concept_results.get('errors', []))
                
            # Handle conflicts if bidirectional
            if direction == SyncDirection.BIDIRECTIONAL:
                conflicts = await self._resolve_conflicts()
                results['conflicts_resolved'] = len(conflicts)
                
            # Update sync state
            self.sync_state['last_sync'] = datetime.utcnow().isoformat()
            self.sync_state['total_synced'] += (
                results['pg_to_concepts'] + results['concepts_to_pg']
            )
            
            # Create checkpoint
            await self._create_checkpoint()
            
            results['end_time'] = datetime.utcnow().isoformat()
            results['duration'] = (
                datetime.utcnow() - start_time
            ).total_seconds()
            
            logger.info(f"Sync completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            self.sync_state['sync_in_progress'] = False
            
    async def _detect_changes(
        self,
        tables: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Detect changes since last sync"""
        changes = {
            'pg_changes': [],
            'concept_changes': []
        }
        
        last_sync = self.sync_state.get('last_sync')
        if not last_sync:
            # First sync, consider everything as changed
            return {
                'pg_changes': ['all'],
                'concept_changes': ['all']
            }
            
        last_sync_time = datetime.fromisoformat(last_sync)
        
        # Detect PostgreSQL changes
        pg_changes = await self._detect_pg_changes(last_sync_time, tables)
        changes['pg_changes'] = pg_changes
        
        # Detect concept changes
        concept_changes = await self._detect_concept_changes(last_sync_time)
        changes['concept_changes'] = concept_changes
        
        return changes
        
    async def _detect_pg_changes(
        self,
        since: datetime,
        tables: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Detect changes in PostgreSQL since given time"""
        changes = []
        
        # Query for tables with updated_at columns
        if not tables:
            tables_query = """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            """
            table_results = await self.pg_storage.execute_query(tables_query)
            tables = [t['tablename'] for t in table_results]
            
        for table in tables:
            try:
                # Check if table has updated_at column
                schema = await self.pg_storage.get_table_schema(table)
                has_updated_at = any(
                    col['column_name'] == 'updated_at' 
                    for col in schema
                )
                
                if has_updated_at:
                    # Query for recent changes
                    query = f"""
                    SELECT COUNT(*) as change_count
                    FROM {table}
                    WHERE updated_at > $1
                    """
                    result = await self.pg_storage.execute_query(
                        query, 
                        [since]
                    )
                    
                    if result and result[0]['change_count'] > 0:
                        changes.append({
                            'table': table,
                            'change_count': result[0]['change_count'],
                            'type': 'update'
                        })
                        
            except Exception as e:
                logger.warning(f"Failed to detect changes in {table}: {e}")
                
        return changes
        
    async def _detect_concept_changes(
        self,
        since: datetime
    ) -> List[Dict[str, Any]]:
        """Detect changes in concept layer since given time"""
        # This would query the vector store for recent changes
        # Implementation depends on vector store capabilities
        changes = []
        
        # For now, track changes through our change log
        for change in self.change_log:
            if datetime.fromisoformat(change['timestamp']) > since:
                changes.append(change)
                
        return changes
        
    async def _sync_pg_to_concepts(
        self,
        tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Sync changes from PostgreSQL to Concept layer"""
        results = {
            'synced_count': 0,
            'errors': [],
            'tables_processed': []
        }
        
        try:
            if not tables:
                # Get all tables
                tables_query = """
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                AND tablename NOT IN ('migrations', 'schema_versions')
                """
                table_results = await self.pg_storage.execute_query(tables_query)
                tables = [t['tablename'] for t in table_results]
                
            for table in tables:
                logger.info(f"Syncing table {table} to concepts")
                
                # Extract concepts from table data
                extraction_result = await self.data_extractor.extract_from_table(
                    table,
                    sample_size=self.batch_size
                )
                
                if extraction_result['success']:
                    results['synced_count'] += extraction_result.get(
                        'concepts_extracted', 0
                    )
                    results['tables_processed'].append(table)
                    
                    # Log the change
                    self._log_change({
                        'type': 'pg_to_concepts',
                        'table': table,
                        'concepts_created': extraction_result.get('concepts_extracted', 0),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                else:
                    results['errors'].append({
                        'table': table,
                        'error': extraction_result.get('error', 'Unknown error')
                    })
                    
        except Exception as e:
            logger.error(f"PG to Concepts sync failed: {e}")
            results['errors'].append(str(e))
            
        return results
        
    async def _sync_concepts_to_pg(
        self,
        tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Sync changes from Concept layer to PostgreSQL"""
        results = {
            'synced_count': 0,
            'errors': [],
            'mappings_created': []
        }
        
        try:
            # Get recent concepts
            recent_concepts = await self._get_recent_concepts()
            
            for concept in recent_concepts:
                # Create or update concept mapping in PostgreSQL
                if concept.get('source_table'):
                    await self.pg_storage.update_concept_mapping(
                        table_name=concept['source_table'],
                        column_name='*',
                        concept_id=concept['id'],
                        confidence=concept.get('confidence', 0.5)
                    )
                    
                    results['synced_count'] += 1
                    results['mappings_created'].append({
                        'concept': concept['name'],
                        'table': concept['source_table']
                    })
                    
                    # Log the change
                    self._log_change({
                        'type': 'concepts_to_pg',
                        'concept': concept['name'],
                        'table': concept.get('source_table'),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
        except Exception as e:
            logger.error(f"Concepts to PG sync failed: {e}")
            results['errors'].append(str(e))
            
        return results
        
    async def _get_recent_concepts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recently created or modified concepts"""
        # This would query the vector store for recent concepts
        # For now, return empty list as placeholder
        return []
        
    async def _resolve_conflicts(self) -> List[Dict[str, Any]]:
        """Resolve conflicts between layers"""
        conflicts = []
        
        # Detect conflicts by comparing checksums
        for change in self.change_log:
            if change['type'] == 'conflict':
                # Resolve based on timestamp (last write wins)
                resolution = await self._resolve_single_conflict(change)
                conflicts.append(resolution)
                
        return conflicts
        
    async def _resolve_single_conflict(
        self,
        conflict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve a single conflict"""
        # Last write wins strategy
        pg_timestamp = conflict.get('pg_timestamp')
        concept_timestamp = conflict.get('concept_timestamp')
        
        if pg_timestamp > concept_timestamp:
            # PostgreSQL wins, update concepts
            return {
                'resolution': 'pg_wins',
                'action': 'update_concepts',
                'conflict': conflict
            }
        else:
            # Concepts win, update PostgreSQL
            return {
                'resolution': 'concepts_win',
                'action': 'update_pg',
                'conflict': conflict
            }
            
    async def _create_checkpoint(self) -> None:
        """Create a sync checkpoint"""
        checkpoint = {
            'timestamp': datetime.utcnow().isoformat(),
            'sync_state': self.sync_state.copy(),
            'change_log_size': len(self.change_log)
        }
        
        # Store checkpoint
        checkpoint_id = hashlib.md5(
            checkpoint['timestamp'].encode()
        ).hexdigest()
        self.sync_checkpoints[checkpoint_id] = checkpoint
        
        # Trim old checkpoints (keep last 10)
        if len(self.sync_checkpoints) > 10:
            oldest = sorted(self.sync_checkpoints.keys())[:1]
            for key in oldest:
                del self.sync_checkpoints[key]
                
    def _log_change(self, change: Dict[str, Any]) -> None:
        """Log a change for tracking"""
        self.change_log.append(change)
        
        # Trim log if too large (keep last 1000 entries)
        if len(self.change_log) > 1000:
            self.change_log = self.change_log[-1000:]
            
    async def schedule_sync(
        self,
        interval_minutes: int = 30,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    ) -> None:
        """Schedule periodic synchronization"""
        while True:
            await asyncio.sleep(interval_minutes * 60)
            await self.sync(direction=direction)
            
    async def real_time_sync(self) -> None:
        """Enable real-time synchronization"""
        self.mode = SyncMode.REAL_TIME
        logger.info("Real-time sync enabled")
        
        # Would set up database triggers and change data capture
        # This is a placeholder for the actual implementation
        
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            'mode': self.mode.value,
            'last_sync': self.sync_state.get('last_sync'),
            'sync_in_progress': self.sync_state.get('sync_in_progress'),
            'total_synced': self.sync_state.get('total_synced'),
            'pending_changes': len(self.sync_state.get('pending_pg_changes', [])) + 
                            len(self.sync_state.get('pending_concept_changes', [])),
            'recent_errors': self.sync_state.get('errors', [])[-5:],
            'checkpoints': len(self.sync_checkpoints)
        }
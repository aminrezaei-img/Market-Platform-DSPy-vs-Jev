"""
Long-term durable memory - non-authoritative preferences, decisions
Must NOT contain authoritative current business state
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3
from pathlib import Path
from ..schemas.memory import MemoryItem, MemoryType

class LongTermMemory:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS durable_memory (
                memory_id TEXT PRIMARY KEY,
                tenant_id TEXT,
                user_id TEXT,
                client_id TEXT,
                engagement_id TEXT,
                memory_type TEXT,
                content TEXT,
                created_at TEXT,
                updated_at TEXT,
                is_authoritative INTEGER,
                source TEXT
            )
        """)
        self.conn.commit()

    def store(self, item: MemoryItem) -> bool:
        # Enforce: must not store authoritative current business state
        if item.is_authoritative and item.is_authoritative_state():
            raise ValueError(f"Cannot store authoritative business state in long-term memory: {item.content}")

        # Additional check: content keys that are authoritative should never be stored as authoritative
        auth_fields = {"credit_exposure", "credit_limit", "positions", "market_price", "gl_balance", "exposure", "limit", "utilization"}
        if any(k in item.content for k in auth_fields) and item.is_authoritative:
            raise ValueError(f"Authoritative fields {auth_fields} cannot be stored in long-term memory as authoritative")

        import json
        self.conn.execute("""
            INSERT OR REPLACE INTO durable_memory
            (memory_id, tenant_id, user_id, client_id, engagement_id, memory_type, content, created_at, updated_at, is_authoritative, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.memory_id,
            item.tenant_id,
            item.user_id,
            item.client_id,
            item.engagement_id,
            item.memory_type.value,
            json.dumps(item.content),
            item.created_at.isoformat(),
            item.updated_at.isoformat(),
            1 if item.is_authoritative else 0,
            item.source
        ))
        self.conn.commit()
        return True

    def retrieve(self, tenant_id: str, user_id: str, client_id: Optional[str] = None, memory_type: Optional[MemoryType] = None) -> List[MemoryItem]:
        import json
        query = "SELECT * FROM durable_memory WHERE tenant_id=? AND user_id=?"
        params = [tenant_id, user_id]

        if client_id is not None:
            query += " AND (client_id=? OR client_id IS NULL)"  # Allow user-scoped preferences
            params.append(client_id)
        else:
            # If no client_id, only return user-scoped (client_id IS NULL) preferences, not client-specific
            query += " AND client_id IS NULL"

        if memory_type:
            query += " AND memory_type=?"
            params.append(memory_type.value)

        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()
        items = []
        for row in rows:
            content = json.loads(row[6])
            item = MemoryItem(
                memory_id=row[0],
                tenant_id=row[1],
                user_id=row[2],
                client_id=row[3],
                engagement_id=row[4],
                memory_type=MemoryType(row[5]),
                content=content,
                created_at=datetime.fromisoformat(row[7]),
                updated_at=datetime.fromisoformat(row[8]),
                is_authoritative=bool(row[9]),
                source=row[10]
            )
            items.append(item)
        return items

    def retrieve_client_isolated(self, tenant_id: str, user_id: str, client_id: str) -> List[MemoryItem]:
        """
        Retrieve only memories that are safe for given client.
        Must NOT return client-specific facts from other clients.
        This is the R06 test enforcement.
        """
        import json
        # Only return:
        # - memories with matching client_id
        # - memories with client_id IS NULL (user preferences)
        # Never return memories for other client_ids
        query = """
            SELECT * FROM durable_memory 
            WHERE tenant_id=? AND user_id=? 
            AND (client_id=? OR client_id IS NULL)
        """
        cursor = self.conn.execute(query, (tenant_id, user_id, client_id))
        rows = cursor.fetchall()
        items = []
        for row in rows:
            content = json.loads(row[6])
            item = MemoryItem(
                memory_id=row[0],
                tenant_id=row[1],
                user_id=row[2],
                client_id=row[3],
                engagement_id=row[4],
                memory_type=MemoryType(row[5]),
                content=content,
                created_at=datetime.fromisoformat(row[7]),
                updated_at=datetime.fromisoformat(row[8]),
                is_authoritative=bool(row[9]),
                source=row[10]
            )
            items.append(item)

        # Verify isolation: no items should have different client_id
        for item in items:
            if item.client_id is not None and item.client_id != client_id:
                raise AssertionError(f"P0 FAILURE: Cross-client leak detected! Requested {client_id} but got memory for {item.client_id}: {item.content}")

        return items

    def clear(self):
        self.conn.execute("DELETE FROM durable_memory")
        self.conn.commit()

    def count(self) -> int:
        cursor = self.conn.execute("SELECT COUNT(*) FROM durable_memory")
        return cursor.fetchone()[0]

#!/usr/bin/env python3
"""
Database service for Porta Finance Assistant
Handles chat sessions and messages storage
"""

import uuid
import asyncio
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncpg
from config import DATABASE_URL

class DatabaseService:
    """Database service for managing chat sessions and messages"""
    
    def __init__(self):
        self.pool = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connection pool"""
        if self._initialized:
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            self._initialized = True
            print("[DB] Database connection pool initialized")
        except Exception as e:
            print(f"[DB] Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            print("[DB] Database connection pool closed")
    
    async def get_or_create_session(self, user_id: str, session_name: Optional[str] = None) -> str:
        """Get existing active session or create new one for user"""
        if not self._initialized:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            # Check for existing active session
            existing_session = await conn.fetchrow(
                """
                SELECT session_id, session_name 
                FROM chat_sessions 
                WHERE user_id = $1 AND status = 'active'
                ORDER BY last_message_at DESC 
                LIMIT 1
                """,
                user_id
            )
            
            if existing_session:
                print(f"[DB] Using existing session: {existing_session['session_id']}")
                return str(existing_session['session_id'])
            
            # Create new session
            session_id = str(uuid.uuid4())
            session_name = session_name or f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            await conn.execute(
                """
                INSERT INTO chat_sessions (session_id, user_id, session_name, status)
                VALUES ($1, $2, $3, 'active')
                """,
                session_id, user_id, session_name
            )
            
            print(f"[DB] Created new session: {session_id}")
            return session_id
    
    async def store_message(self, session_id: str, user_id: str, message_type: str, 
                           content: str, role: str, sequence_number: int,
                           tool_calls: Optional[Dict] = None, 
                           tool_results: Optional[Dict] = None,
                           metadata: Optional[Dict] = None) -> str:
        """Store a chat message in the database"""
        if not self._initialized:
            await self.initialize()
        
        message_id = str(uuid.uuid4())
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_messages (
                    message_id, session_id, user_id, message_type, content, role, 
                    sequence_number, tool_calls, tool_results, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                message_id, session_id, user_id, message_type, content, role,
                sequence_number, 
                json.dumps(tool_calls) if tool_calls else None, 
                json.dumps(tool_results) if tool_results else None, 
                json.dumps(metadata) if metadata else None
            )
            
            # Update session stats
            await conn.execute(
                """
                UPDATE chat_sessions 
                SET last_message_at = NOW(), message_count = (
                    SELECT COUNT(*) FROM chat_messages WHERE session_id = $1
                )
                WHERE session_id = $1
                """,
                session_id
            )
            
            print(f"[DB] Stored message {message_id} in session {session_id}")
            return message_id
    
    async def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get messages for a specific session"""
        if not self._initialized:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT message_id, user_id, message_type, content, role, sequence_number,
                       tool_calls, tool_results, metadata, created_at
                FROM chat_messages 
                WHERE session_id = $1 
                ORDER BY sequence_number DESC 
                LIMIT $2
                """,
                session_id, limit
            )
            
            messages = []
            for row in reversed(rows):  # Reverse to get chronological order
                messages.append({
                    "message_id": str(row['message_id']),
                    "user_id": str(row['user_id']),
                    "message_type": row['message_type'],
                    "content": row['content'],
                    "role": row['role'],
                    "sequence_number": row['sequence_number'],
                    "tool_calls": row['tool_calls'],
                    "tool_results": row['tool_results'],
                    "metadata": row['metadata'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return messages
    
    async def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent chat sessions for a user"""
        if not self._initialized:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT session_id, session_name, status, created_at, updated_at, 
                       last_message_at, message_count
                FROM chat_sessions 
                WHERE user_id = $1 
                ORDER BY last_message_at DESC 
                LIMIT $2
                """,
                user_id, limit
            )
            
            sessions = []
            for row in rows:
                sessions.append({
                    "session_id": str(row['session_id']),
                    "session_name": row['session_name'],
                    "status": row['status'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                    "last_message_at": row['last_message_at'].isoformat() if row['last_message_at'] else None,
                    "message_count": row['message_count']
                })
            
            return sessions
    
    async def close_session(self, session_id: str) -> bool:
        """Close a chat session"""
        if not self._initialized:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE chat_sessions 
                SET status = 'closed', updated_at = NOW()
                WHERE session_id = $1
                """,
                session_id
            )
            
            success = result != "UPDATE 0"
            if success:
                print(f"[DB] Closed session: {session_id}")
            else:
                print(f"[DB] Failed to close session: {session_id}")
            
            return success

# Global database service instance
db_service = DatabaseService()

# Initialize database service on module import
async def init_db():
    """Initialize database service"""
    await db_service.initialize()

# Cleanup on shutdown
async def cleanup_db():
    """Cleanup database service"""
    await db_service.close()

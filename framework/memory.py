# memory.py

import aiosqlite
import datetime
import pickle
import os
import asyncio
import contextvars
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import AsyncOpenAI

current_activity_id = contextvars.ContextVar('current_activity_id', default=None)

class Memory:
    def __init__(self, db_name='memory.db'):
        self.db_name = db_name
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not self.client.api_key:
            print("OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")

    def get_db_connection(self):
        return aiosqlite.connect(self.db_name)

    async def initialize(self):
        async with self.get_db_connection() as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_id TEXT,
                    timestamp TEXT NOT NULL,
                    activity TEXT NOT NULL,
                    result TEXT,
                    start_time REAL,
                    end_time REAL,
                    duration REAL,
                    state_changes TEXT,
                    final_state TEXT,
                    embedding BLOB,
                    source TEXT,
                    parent_id INTEGER
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS state_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    energy INTEGER,
                    happiness INTEGER,
                    xp INTEGER
                )
            ''')
            await db.commit()

    async def get_all_activity_logs(self):
        async with self.get_db_connection() as db:
            cursor = await db.execute('''
                SELECT timestamp, activity, result, duration, state_changes, source 
                FROM activity_logs
                ORDER BY timestamp ASC
            ''')
            rows = await cursor.fetchall()

        logs = []
        for row in rows:
            timestamp, activity, result, duration, state_changes_str, source = row
            state_changes = json.loads(state_changes_str) if state_changes_str else {}
            logs.append({
                'timestamp': timestamp,
                'activity': activity,
                'result': result,
                'duration': duration,
                'state_changes': state_changes,
                'source': source or 'system'
            })
        return logs

    async def store_activity(self, entry):
        import json
        state_changes_str = json.dumps(entry.get('state_changes', {}))
        final_state_str = json.dumps(entry.get('final_state', {}))
        embedding = await self.compute_embedding(entry.get('result', ''))
        embedding_blob = pickle.dumps(embedding)

        async with self.get_db_connection() as db:
            await db.execute('''
                INSERT INTO activity_logs (
                    activity_id, timestamp, activity, result, start_time, end_time, duration,
                    state_changes, final_state, embedding, source, parent_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.get('activity_id'),
                datetime.datetime.now().isoformat(),
                entry.get('activity'),
                entry.get('result'),
                entry.get('start_time'),
                entry.get('end_time'),
                entry.get('duration'),
                state_changes_str,
                final_state_str,
                embedding_blob,
                entry.get('source', 'core_loop'),
                entry.get('parent_id')
            ))
            await db.commit()

    async def store_memory(self, content, activity, source='activity'):
        embedding = await self.compute_embedding(content)
        embedding_blob = pickle.dumps(embedding)
        activity_id = current_activity_id.get()

        async with self.get_db_connection() as db:
            await db.execute('''
                INSERT INTO activity_logs (
                    activity_id, timestamp, activity, result, embedding, source, parent_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                activity_id,
                datetime.datetime.now().isoformat(),
                activity,
                content,
                embedding_blob,
                source,
                None
            ))
            await db.commit()

    async def store_state_snapshot(self, state):
        timestamp = datetime.datetime.now().isoformat()
        async with self.get_db_connection() as db:
            await db.execute('''
                INSERT INTO state_snapshots (timestamp, energy, happiness, xp)
                VALUES (?, ?, ?, ?)
            ''', (
                timestamp,
                state.energy,
                state.happiness,
                state.xp
            ))
            await db.commit()

    async def compute_embedding(self, text):
        if not self.client.api_key or not text.strip():
            return None
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error computing embedding: {e}")
            return None

    async def find_similar_memories(self, text, top_n=5, activity_type=None, source=None):
        query_embedding = await self.compute_embedding(text)
        if query_embedding is None:
            return []

        async with self.get_db_connection() as db:
            sql = 'SELECT id, activity, result, embedding, source FROM activity_logs WHERE embedding IS NOT NULL'
            params = []
            if activity_type:
                sql += ' AND activity = ?'
                params.append(activity_type)
            if source:
                sql += ' AND source = ?'
                params.append(source)

            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()

        similarities = []
        for row in rows:
            id, activity, result, embedding_blob, memory_source = row
            embedding = pickle.loads(embedding_blob)
            sim = cosine_similarity([query_embedding], [embedding])[0][0]
            similarities.append((sim, {
                'id': id,
                'activity': activity,
                'result': result,
                'source': memory_source
            }))

        similarities.sort(key=lambda x: x[0], reverse=True)
        top_memories = [item[1] for item in similarities[:top_n]]
        return top_memories

    async def get_last_activity_time(self, activity_name):
        async with self.get_db_connection() as db:
            cursor = await db.execute('''
                SELECT timestamp FROM activity_logs
                WHERE activity = ?
                ORDER BY id DESC
                LIMIT 1
            ''', (activity_name,))
            row = await cursor.fetchone()
            if row:
                timestamp_str = row[0]
                timestamp = datetime.datetime.fromisoformat(timestamp_str)
                return timestamp
            else:
                return None

    async def count_activity_occurrences(self, activity_name, since):
        async with self.get_db_connection() as db:
            cursor = await db.execute('''
                SELECT COUNT(*) FROM activity_logs
                WHERE activity = ? AND timestamp >= ?
            ''', (activity_name, since.isoformat()))
            row = await cursor.fetchone()
            if row:
                return row[0]
            else:
                return 0

    async def has_activity_occurred(self, activity_name, since):
        count = await self.count_activity_occurrences(activity_name, since)
        return count > 0

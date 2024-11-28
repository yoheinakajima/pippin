# memory.py

import aiosqlite
import datetime
import pickle
import os
import asyncio
import contextvars
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import AsyncOpenAI

# Context variable for current activity_id
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
        async with aiosqlite.connect(self.db_name) as db:
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

    async def store_activity(self, entry):
        # Convert state_changes and final_state to strings (JSON)
        import json
        state_changes_str = json.dumps(entry.get('state_changes', {}))
        final_state_str = json.dumps(entry.get('final_state', {}))

        # Compute embedding of the result
        result_text = entry.get('result', '')
        embedding = await self.compute_embedding(result_text)
        embedding_blob = pickle.dumps(embedding)

        async with aiosqlite.connect(self.db_name) as db:
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
                entry.get('source', 'core_loop'),  # Default to 'core_loop' if not specified
                entry.get('parent_id')
            ))
            await db.commit()

    async def store_memory(self, content, activity, source='activity'):
        # Compute embedding
        embedding = await self.compute_embedding(content)
        embedding_blob = pickle.dumps(embedding)

        # Get current activity_id from context
        activity_id = current_activity_id.get()

        async with aiosqlite.connect(self.db_name) as db:
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
                None  # Set parent_id if needed
            ))
            await db.commit()

    async def store_state_snapshot(self, state):
        """Store a snapshot of the current state."""
        timestamp = datetime.datetime.now().isoformat()
        async with aiosqlite.connect(self.db_name) as db:
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
        """Compute embedding using the OpenAI API"""
        if not self.client.api_key:
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
        # Compute embedding of the input text
        query_embedding = await self.compute_embedding(text)
        if query_embedding is None:
            return []

        # Fetch embeddings from the database with optional filters
        async with aiosqlite.connect(self.db_name) as db:
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

        # Compute similarities
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

        # Sort and return top N
        similarities.sort(key=lambda x: x[0], reverse=True)
        top_memories = [item[1] for item in similarities[:top_n]]
        return top_memories
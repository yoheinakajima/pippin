# memory.py

import aiosqlite
import datetime

class Memory:
    def __init__(self, db_name='memory.db'):
        self.db_name = db_name


    def get_db_connection(self):
        return aiosqlite.connect(self.db_name)

    async def initialize(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    activity TEXT NOT NULL,
                    result TEXT,
                    start_time REAL,
                    end_time REAL,
                    duration REAL,
                    state_changes TEXT,
                    final_state TEXT
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

        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''
                INSERT INTO activity_logs (
                    timestamp, activity, result, start_time, end_time, duration,
                    state_changes, final_state
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.datetime.now().isoformat(),
                entry.get('activity'),
                entry.get('result'),
                entry.get('start_time'),
                entry.get('end_time'),
                entry.get('duration'),
                state_changes_str,
                final_state_str
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

# activities/memory_summary.py

import asyncio

async def run(state, memory):
    """
    Activity: Memory Summary
    Description: Summarizes the character's memories.
    """
    # Simulate processing time
    await asyncio.sleep(2)

    # Fetch all activity logs
    async with memory.get_db_connection() as db:
        cursor = await db.execute('SELECT activity, COUNT(*) FROM activity_logs GROUP BY activity')
        rows = await cursor.fetchall()
        total_memories = sum(count for _, count in rows)
        memory_summary = {activity: count for activity, count in rows}

    # Update state or perform actions based on memory summary
    state.xp += total_memories  # For example, gain XP based on number of memories

    # Store activity result
    entry = {
        'activity': 'memory_summary',
        'result': f'Summarized {total_memories} memories',
        'energy': state.energy,
        'happiness': state.happiness,
        'xp': state.xp,
        'memory_summary': memory_summary
    }
    await memory.store_activity(entry)

# activities/memory_summary.py
import asyncio
import json

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

    # Create the result content as a string
    result_content = {
        'total_memories': total_memories,
        'memory_breakdown': memory_summary,
        'state_snapshot': {
            'energy': state.energy,
            'happiness': state.happiness,
            'xp': state.xp
        }
    }

    # Convert to string for storage
    content = json.dumps(result_content, indent=2)

    # Store the memory with the required arguments
    await memory.store_memory(
        content=content,
        activity='memory_summary',
        source='activity'
    )

    return f"Summarized {total_memories} memories"
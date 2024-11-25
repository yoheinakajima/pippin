# activities/template_activity.py

import asyncio
import random

async def run(state, memory):
    """
    Activity: Template Activity
    Description: This is a template for creating new activities.
    """

    # Simulate activity duration
    duration = random.randint(1, 3)  # Duration in seconds
    await asyncio.sleep(duration)  # Simulate time passing

    # Access and modify state variables
    state.energy = max(state.energy - 10, 0)  # Decrease energy
    state.happiness = min(state.happiness + 5, 100)  # Increase happiness
    state.xp += 5  # Increase experience points

    # Access memories
    # Fetch the last 5 activity logs
    async with memory.get_db_connection() as db:
        cursor = await db.execute('''
            SELECT activity, result, timestamp
            FROM activity_logs
            ORDER BY id DESC
            LIMIT 5
        ''')
        recent_memories = await cursor.fetchall()

    # Process memories (example: print or analyze them)
    # For this template, we'll just count them
    memory_count = len(recent_memories)

    # Store the result of the activity
    entry = {
        'activity': 'template_activity',
        'result': f'Processed {memory_count} recent memories',
        'energy': state.energy,
        'happiness': state.happiness,
        'xp': state.xp
    }
    await memory.store_activity(entry)

    # Additional actions can be performed here
    # e.g., interacting with external APIs, triggering events, etc.

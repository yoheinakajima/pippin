# activities/nap.py

import asyncio
import random

async def run(state, memory):
    """
    Activity: Nap
    Description: The character takes a nap to restore energy.
    """
    duration = random.randint(1, 3)
    await asyncio.sleep(duration*50)
    state.energy = min(state.energy + 30, 100)
    entry = {
        'activity': 'nap',
        'result': 'rested',
        'energy': state.energy,
        'happiness': state.happiness,
        'xp': state.xp
    }
    await memory.store_activity(entry)

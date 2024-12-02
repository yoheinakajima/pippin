# activities/play.py

import asyncio
import random

async def run(state, memory):
    """
    Activity: Play
    Description: The character engages in a fun activity to increase happiness at the cost of some energy.
    """
    # Simulate activity duration
    duration = random.randint(1, 2)  # Duration in seconds
    await asyncio.sleep(duration*10)  # Simulate time taken to play

    # Modify state variables
    state.energy = max(state.energy - 10, 0)  # Decrease energy by 10, minimum 0
    state.happiness = min(state.happiness + 20, 100)  # Increase happiness by 20, maximum 100

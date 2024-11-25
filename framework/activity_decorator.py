# framework/activity_decorator.py

import asyncio
import time
from copy import deepcopy
from functools import wraps

def activity_wrapper(func):
    @wraps(func)
    async def wrapper(state, memory):
        # Record start time
        start_time = time.time()

        # Make a deep copy of the state before the activity
        state_before = deepcopy(state.to_dict())

        # Run the activity function
        await func(state, memory)

        # Record end time
        end_time = time.time()
        duration = end_time - start_time  # Duration in seconds

        # Determine which state variables have changed
        state_after = state.to_dict()
        state_changes = {
            key: state_after[key]
            for key in state_after
            if state_after[key] != state_before.get(key)
        }

        # Prepare the activity log entry
        activity_name = func.__module__.split('.')[-1]
        entry = {
            'activity': activity_name,
            'result': 'completed',
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'state_changes': state_changes,
            'final_state': state_after
        }

        # Store the activity log entry
        await memory.store_activity(entry)

    return wrapper

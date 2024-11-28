# framework/activity_decorator.py

import asyncio
import time
from copy import deepcopy
from functools import wraps
import uuid
import contextvars

# Context variable to store the current activity_id
current_activity_id = contextvars.ContextVar('current_activity_id', default=None)

def activity_wrapper(func):
    @wraps(func)
    async def wrapper(state, memory):
        # Generate a unique activity_id
        activity_id = str(uuid.uuid4())
        current_activity_id.set(activity_id)

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
            'activity_id': activity_id,
            'activity': activity_name,
            'result': 'completed',
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'state_changes': state_changes,
            'final_state': state_after,
            'source': 'core_loop',
            'parent_id': None  # No parent for core loop activities
        }

        # Store the activity log entry
        await memory.store_activity(entry)

    return wrapper

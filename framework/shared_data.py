# shared_data.py

from framework.state import State

state = State()
current_activity = {
    'name': None,
    'start_time': None  # Store the start time as a UNIX timestamp
}
activity_history = []
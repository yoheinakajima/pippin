# activity_selector.py

import random

def select_activity(state, activity_functions):
    activities = list(activity_functions.keys())
    probabilities = []

    # Adjust probabilities based on state
    if state.energy < 30 and 'nap' in activities:
        probabilities = [0.6 if a == 'nap' else 0.2 for a in activities]
    elif state.happiness < 40 and 'play' in activities:
        probabilities = [0.6 if a == 'play' else 0.2 for a in activities]
    else:
        probabilities = [1 / len(activities)] * len(activities)  # Equal probability

    activity = random.choices(activities, probabilities)[0]
    return activity

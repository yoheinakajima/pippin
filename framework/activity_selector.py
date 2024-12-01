# activity_selector.py

import random
import time
from datetime import datetime, timedelta
from framework.activity_constraints import constraints

IGNORED_ACTIVITIES = [
    'template_activity',
    'memory_summary',
    # Uncomment activities you want to ignore
    # 'take_a_walk',
    # 'nap',
    # 'draw',
    # 'play'
]

async def select_activity(state, activity_functions, memory, additional_ignored_activities=None):
    ignored = set(IGNORED_ACTIVITIES)
    if additional_ignored_activities:
        ignored.update(additional_ignored_activities)

    # Get all available activities excluding ignored ones
    available_activities = [act for act in activity_functions.keys() if act not in ignored]
    if not available_activities:
        raise ValueError("No activities available after applying ignore list")

    # Filter activities based on constraints
    filtered_activities = []
    for activity in available_activities:
        is_allowed = await is_activity_allowed(activity, memory)
        if is_allowed:
            filtered_activities.append(activity)

    if not filtered_activities:
        raise ValueError("No activities available after applying constraints")

    # Reconstruct available_activities to only include allowed activities
    available_activities = filtered_activities

    # Initialize probabilities
    base_prob = 1.0 / len(available_activities)
    probabilities = [base_prob] * len(available_activities)

    # Get indices for all activities
    activity_indices = {}
    for idx, activity in enumerate(available_activities):
        activity_indices[activity] = idx

    # Now get indices for specific activities
    nap_index = activity_indices.get('nap')
    play_index = activity_indices.get('play')
    walk_index = activity_indices.get('take_a_walk')
    draw_index = activity_indices.get('draw')
    tweet_index = activity_indices.get('post_a_tweet')

    # Adjust probabilities based on state
    if state.energy < 30:
        # Low energy -> Higher chance of nap, lower chance of active activities
        if nap_index is not None:
            probabilities = [0.6 if i == nap_index else 0.1 for i in range(len(available_activities))]
            if draw_index is not None:
                probabilities[draw_index] = 0.05  # Less likely to draw when tired
            if tweet_index is not None:
                probabilities[tweet_index] = 0.05  # Less likely to tweet when tired
        else:
            # If nap is not available, adjust probabilities uniformly
            probabilities = [1.0 / len(available_activities)] * len(available_activities)

    elif state.happiness < 40:
        # Low happiness -> Higher chance of creative/social activities
        boost = 0.3
        for idx in range(len(available_activities)):
            probabilities[idx] = 0.1  # Set a base low probability
        if draw_index is not None:
            probabilities[draw_index] += boost  # Drawing helps express feelings
        if tweet_index is not None:
            probabilities[tweet_index] += boost  # Sharing helps connect
        if play_index is not None:
            probabilities[play_index] += boost
        if walk_index is not None:
            probabilities[walk_index] += boost

    elif 30 <= state.energy <= 70:
        # Medium energy -> Good mix of activities
        for idx in range(len(available_activities)):
            probabilities[idx] = 1.0 / len(available_activities)  # Reset to uniform distribution
        if walk_index is not None:
            probabilities[walk_index] += 0.1
        if draw_index is not None:
            probabilities[draw_index] += 0.1  # Good energy for creative activities
        if tweet_index is not None:
            probabilities[tweet_index] += 0.1  # Good time to share thoughts

    elif state.energy > 70:
        # High energy -> More active and creative activities
        active_boost = 0.2
        for idx in range(len(available_activities)):
            probabilities[idx] = 1.0 / len(available_activities)  # Reset to uniform distribution
        if play_index is not None:
            probabilities[play_index] += active_boost
        if walk_index is not None:
            probabilities[walk_index] += active_boost
        if draw_index is not None:
            probabilities[draw_index] += active_boost
        if tweet_index is not None:
            probabilities[tweet_index] += 0.1

    # Normalize probabilities
    total = sum(probabilities)
    probabilities = [p / total for p in probabilities]

    # Select activity
    selected_activity = random.choices(available_activities, probabilities)[0]
    return selected_activity

async def is_activity_allowed(activity, memory):
    constraint = constraints.get(activity, {})
    frequency_constraints = constraint.get('frequency', {})
    after_constraints = constraint.get('after', {})
    current_time = datetime.now()

    # Check 'max_per_day' constraint
    max_per_day = frequency_constraints.get('max_per_day')
    if max_per_day is not None:
        count = await memory.count_activity_occurrences(
            activity,
            since=current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        )
        if count >= max_per_day:
            return False  # Activity has reached its daily maximum

    # Check 'after' constraints
    for related_activity, min_interval in after_constraints.items():
        last_time = await memory.get_last_activity_time(related_activity)
        if last_time is None:
            continue  # Activity never happened, constraint doesn't apply
        elapsed_time = (current_time - last_time).total_seconds()
        if elapsed_time < min_interval:
            return False  # Constraint violated

    return True  # All constraints satisfied

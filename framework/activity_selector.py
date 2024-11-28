import random

# Activities that should never be selected
IGNORED_ACTIVITIES = [
    'template_activity',  
    'memory_summary' 
]

def select_activity(state, activity_functions, additional_ignored_activities=None):
    """
    Select an activity based on current state and probabilities, respecting ignored activities.

    Args:
        state: Current state object with energy, happiness, etc.
        activity_functions: Dictionary of available activity functions
        additional_ignored_activities: Optional list of additional activities to ignore

    Returns:
        str: Selected activity name
    """
    # Combine default ignored activities with any additional ones
    ignored = set(IGNORED_ACTIVITIES)
    if additional_ignored_activities:
        ignored.update(additional_ignored_activities)

    # Filter out ignored activities
    available_activities = [act for act in activity_functions.keys() if act not in ignored]

    if not available_activities:
        raise ValueError("No activities available after applying ignore list")

    # Base probabilities for all activities
    base_prob = 1.0 / len(available_activities)
    probabilities = [base_prob] * len(available_activities)

    # Get indices for special activities
    activity_indices = {
        'nap': None,
        'play': None,
        'take_walk': None
    }

    for activity in activity_indices.keys():
        try:
            activity_indices[activity] = available_activities.index(activity)
        except ValueError:
            continue

    # Adjust probabilities based on state and time of day
    nap_index = activity_indices['nap']
    play_index = activity_indices['play']
    walk_index = activity_indices['take_walk']

    # Low energy -> Higher chance of nap
    if state.energy < 30 and nap_index is not None:
        probabilities = [0.6 if i == nap_index else 0.2 for i in range(len(available_activities))]

    # Low happiness -> Higher chance of play or walk
    elif state.happiness < 40 and (play_index is not None or walk_index is not None):
        # If both play and walk are available, distribute the probability
        if play_index is not None and walk_index is not None:
            probabilities = [0.4 if i == play_index else 
                           0.3 if i == walk_index else 
                           0.15 for i in range(len(available_activities))]
        # If only one is available, give it higher probability
        elif play_index is not None:
            probabilities = [0.6 if i == play_index else 0.2 for i in range(len(available_activities))]
        elif walk_index is not None:
            probabilities = [0.6 if i == walk_index else 0.2 for i in range(len(available_activities))]

    # Medium energy (30-70) -> Good chance for a walk
    elif 30 <= state.energy <= 70 and walk_index is not None:
        probabilities = [0.4 if i == walk_index else 
                        (1 - 0.4) / (len(available_activities) - 1) for i in range(len(available_activities))]

    # High energy -> Equal distribution but slightly higher for active activities
    elif state.energy > 70 and (play_index is not None or walk_index is not None):
        active_boost = 0.1  # Small boost for active activities
        base = (1.0 - (active_boost * 2)) / (len(available_activities) - 2) if play_index is not None and walk_index is not None else \
               (1.0 - active_boost) / (len(available_activities) - 1)
        probabilities = [base] * len(available_activities)
        if play_index is not None:
            probabilities[play_index] += active_boost
        if walk_index is not None:
            probabilities[walk_index] += active_boost

    # Normalize probabilities to ensure they sum to 1
    total = sum(probabilities)
    probabilities = [p/total for p in probabilities]

    # Select activity
    activity = random.choices(available_activities, probabilities)[0]
    return activity
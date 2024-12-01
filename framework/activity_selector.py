import random

IGNORED_ACTIVITIES = [
    'template_activity',
    'memory_summary',
    #'take_a_walk',
    #'nap',
    #'draw',
    #'play'
]

def select_activity(state, activity_functions, additional_ignored_activities=None):
    ignored = set(IGNORED_ACTIVITIES)
    if additional_ignored_activities:
        ignored.update(additional_ignored_activities)

    available_activities = [act for act in activity_functions.keys() if act not in ignored]
    if not available_activities:
        raise ValueError("No activities available after applying ignore list")

    base_prob = 1.0 / len(available_activities)
    probabilities = [base_prob] * len(available_activities)

    # Get indices for all activities
    activity_indices = {
        'nap': None,
        'play': None,
        'take_a_walk': None,
        'draw': None,
        'post_to_twitter': None
    }

    for activity in activity_indices.keys():
        try:
            activity_indices[activity] = available_activities.index(activity)
        except ValueError:
            continue

    nap_index = activity_indices['nap']
    play_index = activity_indices['play']
    walk_index = activity_indices['take_a_walk']
    draw_index = activity_indices['draw']
    tweet_index = activity_indices['post_to_twitter']

    # Low energy -> Higher chance of nap, lower chance of active activities
    if state.energy < 30:
        if nap_index is not None:
            probabilities = [0.6 if i == nap_index else 0.1 for i in range(len(available_activities))]
            if draw_index is not None:
                probabilities[draw_index] = 0.05  # Less likely to draw when tired
            if tweet_index is not None:
                probabilities[tweet_index] = 0.05  # Less likely to tweet when tired

    # Low happiness -> Higher chance of creative/social activities
    elif state.happiness < 40:
        boost = 0.3
        if draw_index is not None:
            probabilities[draw_index] = boost  # Drawing helps express feelings
        if tweet_index is not None:
            probabilities[tweet_index] = boost  # Sharing helps connect
        if play_index is not None:
            probabilities[play_index] = boost
        if walk_index is not None:
            probabilities[walk_index] = boost

    # Medium energy -> Good mix of activities
    elif 30 <= state.energy <= 70:
        if walk_index is not None:
            probabilities[walk_index] = 0.3
        if draw_index is not None:
            probabilities[draw_index] = 0.2  # Good energy for creative activities
        if tweet_index is not None:
            probabilities[tweet_index] = 0.2  # Good time to share thoughts

    # High energy -> More active and creative activities
    elif state.energy > 70:
        active_boost = 0.25
        if play_index is not None:
            probabilities[play_index] = active_boost
        if walk_index is not None:
            probabilities[walk_index] = active_boost
        if draw_index is not None:
            probabilities[draw_index] = active_boost
        if tweet_index is not None:
            probabilities[tweet_index] = 0.15

    # Normalize probabilities
    total = sum(probabilities)
    probabilities = [p/total for p in probabilities]

    # Select activity
    activity = random.choices(available_activities, probabilities)[0]
    return activity
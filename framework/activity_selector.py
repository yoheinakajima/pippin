import random
from datetime import datetime
from framework.activity_constraints import constraints

# Core logic
IGNORED_ACTIVITIES = [
    'template_activity',
    'memory_summary',
    # Uncomment activities you want to ignore
    #'take_a_walk',
    #'nap',
    'draw',
    #'play',
    'post_a_tweet',
    #'post_a_tweet_with_image',  # Uncommented to treat the same as 'post_a_tweet'
    'read_twitter_mentions'
]

async def get_ignored_activities(additional_ignored=None):
    ignored = set(IGNORED_ACTIVITIES)
    if additional_ignored:
        ignored.update(additional_ignored)
    return ignored

async def filter_activities(activity_functions, ignored_activities):
    return [act for act in activity_functions.keys() if act not in ignored_activities]

async def filter_by_constraints(activities, memory):
    filtered = []
    for activity in activities:
        if await is_activity_allowed(activity, memory):
            filtered.append(activity)
    return filtered

def calculate_probabilities(activities, state, activity_indices):
    base_prob = 1.0 / len(activities)
    probabilities = [base_prob] * len(activities)
    adjust_probabilities_based_on_state(probabilities, state, activity_indices, activities)
    total = sum(probabilities)
    return [p / total for p in probabilities]

def select_random_activity(activities, probabilities):
    return random.choices(activities, probabilities)[0]

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
            return False

    # Check 'after' constraints
    for related_activity, min_interval in after_constraints.items():
        last_time = await memory.get_last_activity_time(related_activity)
        if last_time is None:
            continue
        elapsed_time = (current_time - last_time).total_seconds()
        if elapsed_time < min_interval:
            return False

    return True

# Activity-specific logic
def adjust_probabilities_based_on_state(probabilities, state, activity_indices, activities):
    nap_index = activity_indices.get('nap')
    play_index = activity_indices.get('play')
    walk_index = activity_indices.get('take_a_walk')
    draw_index = activity_indices.get('draw')
    tweet_index = activity_indices.get('post_a_tweet')
    tweet_with_image_index = activity_indices.get('post_a_tweet_with_image')  # Added

    if state.energy < 30:
        if nap_index is not None:
            probabilities = [0.6 if i == nap_index else 0.1 for i in range(len(activities))]
            if draw_index is not None:
                probabilities[draw_index] = 0.05
            if tweet_index is not None:
                probabilities[tweet_index] = 0.05
            if tweet_with_image_index is not None:  # Handle 'post_a_tweet_with_image'
                probabilities[tweet_with_image_index] = 0.05
        else:
            probabilities = [1.0 / len(activities)] * len(activities)
    elif state.happiness < 40:
        boost = 0.3
        for idx in range(len(activities)):
            probabilities[idx] = 0.1
        if draw_index is not None:
            probabilities[draw_index] += boost
        if tweet_index is not None:
            probabilities[tweet_index] += boost
        if tweet_with_image_index is not None:  # Handle 'post_a_tweet_with_image'
            probabilities[tweet_with_image_index] += boost
        if play_index is not None:
            probabilities[play_index] += boost
        if walk_index is not None:
            probabilities[walk_index] += boost
    elif 30 <= state.energy <= 70:
        for idx in range(len(activities)):
            probabilities[idx] = 1.0 / len(activities)
        if walk_index is not None:
            probabilities[walk_index] += 0.1
        if draw_index is not None:
            probabilities[draw_index] += 0.1
        if tweet_index is not None:
            probabilities[tweet_index] += 0.1
        if tweet_with_image_index is not None:  # Handle 'post_a_tweet_with_image'
            probabilities[tweet_with_image_index] += 0.1
    elif state.energy > 70:
        active_boost = 0.2
        for idx in range(len(activities)):
            probabilities[idx] = 1.0 / len(activities)
        if play_index is not None:
            probabilities[play_index] += active_boost
        if walk_index is not None:
            probabilities[walk_index] += active_boost
        if draw_index is not None:
            probabilities[draw_index] += active_boost
        if tweet_index is not None:
            probabilities[tweet_index] += 0.1
        if tweet_with_image_index is not None:  # Handle 'post_a_tweet_with_image'
            probabilities[tweet_with_image_index] += 0.1

# Main function
async def select_activity(state, activity_functions, memory, additional_ignored_activities=None):
    ignored = await get_ignored_activities(additional_ignored_activities)
    available_activities = await filter_activities(activity_functions, ignored)

    if not available_activities:
        raise ValueError("No activities available after applying ignore list")

    filtered_activities = await filter_by_constraints(available_activities, memory)
    if not filtered_activities:
        raise ValueError("No activities available after applying constraints")

    activity_indices = {activity: idx for idx, activity in enumerate(filtered_activities)}
    probabilities = calculate_probabilities(filtered_activities, state, activity_indices)
    selected_activity = select_random_activity(filtered_activities, probabilities)

    return selected_activity

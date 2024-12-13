# activity_constraints.py

constraints = {
    'post_a_tweet_with_image': {
        'frequency': {
            'max_per_day': 8
        },
        'after': {
            'post_a_tweet_with_image': 1 * 3600
        }
    },
    'fetch_recent_stories': {
        'frequency': {
            'max_per_day': 8
        },
        'after': {
            'fetch_recent_stories': 1 * 3600
        }
    }
}

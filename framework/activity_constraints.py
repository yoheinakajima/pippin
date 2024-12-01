# activity_constraints.py

constraints = {
    'post_a_tweet': {
        'frequency': {
            'max_per_day': 3
        },
        'after': {
            'post_a_tweet': 3 * 3600,  # 3 hours in seconds
            'draw': 3 * 3600
        }
    },
    'draw': {
        'frequency': {
            'max_per_day': 3
        },
        'after': {
            'post_a_tweet': 3 * 3600,
            'draw': 3 * 3600
        }
    }
}

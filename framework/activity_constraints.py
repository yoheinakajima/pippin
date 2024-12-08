# activity_constraints.py

constraints = {
    'post_a_tweet_with_image': {
        'frequency': {
            'max_per_day': 3
        },
        'after': {
            'post_a_tweet_with_image': 3 * 3600
        }
    }
}

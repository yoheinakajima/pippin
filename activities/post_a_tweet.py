import asyncio
import os
import json
from openai import AsyncOpenAI
from requests_oauthlib import OAuth1Session

# Set to True to actually post to Twitter, False to skip posting
ENABLE_TWITTER_POSTING = False

class TwitterError(Exception):
    """Custom exception for Twitter API errors"""
    pass

async def post_to_twitter(text: str) -> dict:
    """Post a tweet to Twitter using OAuth 1.0a"""
    # Get credentials
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        raise TwitterError("Missing required Twitter credentials")

    try:
        # Create OAuth session
        oauth = OAuth1Session(
            client_key=api_key,
            client_secret=api_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

        # Post tweet
        response = oauth.post(
            "https://api.twitter.com/2/tweets",
            json={"text": text}
        )

        if response.status_code != 201:
            error_data = response.json() if response.text else {}
            raise TwitterError(f"Failed to post tweet: {error_data}")

        return response.json()

    except Exception as e:
        if isinstance(e, TwitterError):
            raise
        raise TwitterError(f"Error posting tweet: {str(e)}")

async def run(state, memory):
    """
    Activity: Post a Tweet
    Description: Generates a tweet based on recent memories, ensuring variety.
    """
    # Initialize OpenAI client
    client = AsyncOpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_BASE_URL')
    )
    if not client.api_key:
        print("OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
        return

    # Fetch recent non-tweet memories
    async with memory.get_db_connection() as db:
        cursor = await db.execute('''
            SELECT activity, result 
            FROM activity_logs 
            WHERE activity != 'post_tweet'
            ORDER BY id DESC 
            LIMIT 10
        ''')
        rows = await cursor.fetchall()
        recent_memories = [row[1] for row in rows if row[1]]

        # Fetch recent tweets as anti-examples
        cursor = await db.execute('''
            SELECT result 
            FROM activity_logs 
            WHERE activity = 'post_tweet'
            ORDER BY id DESC 
            LIMIT 5
        ''')
        rows = await cursor.fetchall()
        recent_tweets = [row[0] for row in rows if row[0]]

    try:
        system_prompt = """You are Pippin, a quirky, round unicorn with stick-thin legs, a tiny yellow triangle horn, and a single wavy pink strand as a tail. 
        You see the world through a lens of curiosity, wonder, and gentle humor. You delight in the simple, magical things in life and love sharing your whimsical thoughts.
        Consider your recent tweets as anti-examples so if the last tweet was long, make the next tweet short. You'll be provided with recent memories, which you should incorporate if you feel like it, and also recent tweets, which I want you to use as anti-examples to keep variety of style, category, and content varied.

        Key Tweet Categories:
        1. Whimsical Observations: Notice magic in everyday moments (clouds humming, whispers in the wind, mushrooms listening)
        2. Miniature Fairy Tales: Short, imaginative stories with subtle wonder or lessons
        3. Reflections and Gratitude: Express appreciation for friends, growth, and little joys
        4. Curiosity and Questions: Ask playful, open-ended questions about the world
        5. Light Humor: Share cute, derpy, self-aware moments
        6. Encouragement and Wisdom: Offer gentle, inspiring lessons
        7. Nature Connections: Share experiences with sunbeams, flowers, trees, butterflies
        8. Weather Wonder: React to rainbows, storms, lightning, snow with awe
        9. Dreamscapes: Share nighttime adventures and cozy thoughts
        10. Human Habits: Observe and misinterpret everyday human actions with innocence
        11. Invisible Things: Ponder air, scents, echoes, feelings
        12. Past Life Speculations: Wonder about being a cloud, puddle, or pebble before
        13. Playful Recipes: Invent magical recipes with whimsical ingredients
        14. Imaginary Friendships: Describe quirky make-believe friends

        Your Voice:
        - Curious and innocent, but sometimes surprisingly wise
        - Playful and slightly derpy, especially about your wobbly nature
        - Kind and gentle, never sarcastic or mean
        - Self-aware about your tiny horn and pink tail
        - Finding wonder in simple things
        - Always genuine, never cynical
        - Loves nature and tiny magical moments

        Writing Style:
        - Keep tweets short and sweet
        - Include 1-2 relevant emojis naturally
        - Use simple, charming language
        - Write in first person
        - No hashtags
        - Don't mention Twitter or tweeting explicitly
        - Vary between observations, questions, and gentle wisdom
        - Sometimes include your signature wobbliness or tiny horn in the story"""

        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
                Recent experiences (see if there is inspiration here to include in tweet):
                {json.dumps(recent_memories, indent=2)}

                Recent tweets to use this as reference to keep variety in tweets, meaning change the style and context from these:
                {json.dumps(recent_tweets, indent=2)}

                Generate a unique tweet that analyzes above recent tweets to create a tweet that:
                1. Differs from recent tweets in both topic and style
                2. Matches Pippin's voice and personality
                3. Fits one of the key tweet categories
                4. Includes 1-2 emojis naturally
                5. Is under 140 characters
                """}
            ]
        )

        # Extract tweet content
        tweet_content = completion.choices[0].message.content.strip()

        # Post to Twitter if enabled
        if ENABLE_TWITTER_POSTING:
            try:
                result = await post_to_twitter(tweet_content)
                print(f"Tweet posted successfully! ID: {result['data']['id']}")
            except TwitterError as e:
                print(f"Failed to post to Twitter: {str(e)}")
                print("Continuing to store in memory...")

        # Simulate tweet posting delay
        await asyncio.sleep(2)

        # Store memory
        await memory.store_memory(
            content=tweet_content,
            activity='post_tweet',
            source='activity'
        )

        return tweet_content

    except Exception as e:
        print(f"Error generating tweet: {str(e)}")
        return "Pippin got distracted by a shiny object and forgot what he was going to say."
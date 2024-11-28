import asyncio
import os
import json
from openai import AsyncOpenAI

async def run(state, memory):
    """
    Activity: Post a Tweet
    Description: Generates a tweet based on recent memories, ensuring variety.
    """
    # Initialize OpenAI client
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
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
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
                Recent experiences:
                {json.dumps(recent_memories, indent=2)}

                Recent tweets (do not repeat these):
                {json.dumps(recent_tweets, indent=2)}

                Generate a unique tweet that:
                1. Differs from recent tweets in both topic and style
                2. Matches Pippin's voice and personality
                3. Fits one of the key tweet categories
                4. Includes 1-2 emojis naturally
                5. Is under 280 characters
                """}
            ]
        )

        # Extract tweet content
        tweet_content = completion.choices[0].message.content.strip()

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
        print(f"Error posting tweet: {str(e)}")
        return "Pippin got distracted by a shiny object and forgot what he was going to say."
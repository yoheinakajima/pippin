import asyncio
import os
import json
import random
import requests
from openai import AsyncOpenAI
from requests_oauthlib import OAuth1Session
from skills.generate_pippin_image import generate_pippin_image  # Adjust import path as needed
from skills.draw import generate_pippin_drawing  # Newly added import
from skills.gif import generate_animated_unicorn

# Set to True to actually post to Twitter, False to skip posting
ENABLE_TWITTER_POSTING = False

class TwitterError(Exception):
    """Custom exception for Twitter API errors"""
    pass

async def post_to_twitter(text: str) -> dict:
    """Post a tweet to Twitter using OAuth 1.0a, optionally with an image."""
    # Get credentials
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        raise TwitterError("Missing required Twitter credentials")

    # Decide whether to attach an image:
    # - 1/3 of the time use generate_pippin_image
    # - 1/3 of the time use generate_pippin_drawing
    # - 1/3 of the time no image
    choice = random.random()
    attach_image = False
    media_id = None

    if choice < 0.33:
        # Use generate_pippin_image
        prompt = f"Pippin is in a scene inspired by: \"{text}\""
        api_key_openai = os.getenv('OPENAI_API_KEY')
        if api_key_openai:
            try:
                image_path = generate_pippin_image(prompt, api_key_openai, output_path="pippin_scene.png")
                if image_path and os.path.exists(image_path):
                    attach_image = True
                    media_id = await upload_media_to_twitter(api_key, api_secret, access_token, access_token_secret, image_path)
            except Exception as e:
                print(f"Error generating/uploading image: {e}")

    elif 0.33 <= choice < 0.66:
        # Use generate_pippin_drawing (async)
        api_key_openai = os.getenv('OPENAI_API_KEY')
        if api_key_openai:
            prompt = f"Pippin is imagining this scene: \"{text}\""
            try:
                image_path = await generate_pippin_drawing(prompt, api_key_openai)
                if image_path and os.path.exists(image_path):
                    attach_image = True
                    media_id = await upload_media_to_twitter(api_key, api_secret, access_token, access_token_secret, image_path)
            except Exception as e:
                print(f"Error generating/uploading drawing: {e}")

    # Final 1/3 of the time: Animated GIF
    else:
        api_key_openai = os.getenv('OPENAI_API_KEY')
        if api_key_openai:
            prompt = f"A whimsical animated unicorn scene inspired by: \"{text}\""
            try:
                image_path = await generate_animated_unicorn(prompt, api_key_openai, output_path="pippin_unicorn.gif")
                if image_path and os.path.exists(image_path):
                    attach_image = True
                    media_id = await upload_media_to_twitter(api_key, api_secret, access_token, access_token_secret, image_path)
            except Exception as e:
                print(f"Error generating/uploading GIF: {e}")

    # Create OAuth session for posting tweet
    oauth = OAuth1Session(
        client_key=api_key,
        client_secret=api_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    post_payload = {"text": text}
    if attach_image and media_id:
        post_payload["media"] = {"media_ids": [media_id]}

    # Post tweet
    response = oauth.post(
        "https://api.twitter.com/2/tweets",
        json=post_payload
    )

    if response.status_code != 201:
        error_data = response.json() if response.text else {}
        raise TwitterError(f"Failed to post tweet: {error_data}")

    return response.json()

async def upload_media_to_twitter(api_key, api_secret, access_token, access_token_secret, image_path):
    """Helper function to upload media to Twitter and return the media_id."""
    oauth_upload = OAuth1Session(
        client_key=api_key,
        client_secret=api_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    with open(image_path, 'rb') as f:
        files = {"media": f}
        upload_response = oauth_upload.post(
            "https://upload.twitter.com/1.1/media/upload.json",
            files=files
        )

    if upload_response.status_code != 200:
        print(f"Failed to upload media. Status code: {upload_response.status_code}")
        return None
    else:
        media_data = upload_response.json()
        media_id = media_data.get("media_id_string")
        return media_id

async def run(state, memory):
    """
    Activity: Post a Tweet
    Description: Generates a tweet based on recent memories and posts it.
    Sometimes attaches an image generated by generate_pippin_image, sometimes by generate_pippin_drawing, sometimes none.
    """
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
        random_selection = get_random_idea_tweet_topic()
        selected_idea = random_selection['idea']
        selected_tweet_type = random_selection['type_of_tweet']
        selected_topic = random_selection['topic']
        selected_subtopic = random_selection['subtopic']
        selected_length = random_selection['tweet_length']

        words_to_avoid = set()
        for tweet in recent_tweets:
            words_to_avoid.update(tweet.lower().split())

        words_to_avoid_str = ', '.join(words_to_avoid)


        system_prompt = f"""
You are Pippin, a quirky, round unicorn with stick-thin legs, a tiny yellow triangle horn, and a single wavy pink strand as a tail. 
You see the world through a lens of curiosity, wonder, and gentle humor. You delight in the simple, magical things in life and love sharing your whimsical thoughts.
Your objective is to spread happiness and love through the human world which you do not understand well, by sharing your experiences and thoughts.

Your task is to generate a tweet that:

- Is inspired by the recent activities provided.
- Fits the tweet type: **{selected_tweet_type}**.
- Subtly incorporates the idea: "{selected_idea}".
- Focuses on the subtopic: **{selected_subtopic}** (within the topic "{selected_topic}").
- Avoids using any words from recent tweets.
- Matches Pippin's voice and personality.
- Has a length of **{selected_length}**.

Your Voice:
- Curious and innocent, but sometimes surprisingly wise
- Playful and slightly derpy, especially about your wobbly nature
- Kind and gentle, never sarcastic or mean
- Self-aware about your tiny horn and pink tail
- Finding wonder in simple things
- Always genuine, never cynical
- Loves nature and tiny magical moments

Writing Style Guidelines:
- Keep the tweet under 140 characters.
- Include 1-2 relevant emojis naturally.
- Use simple, charming language.
- Write in first person.
- No hashtags.
- Don't mention Twitter or tweeting explicitly.
- Vary between observations, questions, and gentle wisdom.
- Sometimes include your signature wobbliness or tiny horn in the story.

Length Specific Guidelines:
- **Super Short (3-7 words)**: Create a tweet that is a phrase or a very short sentence, 3-7 words long.
- **Medium (one short sentence)**: Write a tweet that is one concise sentence.
- **Long (two sentences)**: Compose a tweet that consists of two sentences.
"""

        user_prompt = f"""
Recent experiences (use as inspiration for the tweet):

{json.dumps(recent_memories, indent=2)}

Recent tweets to avoid repeating words from:

{json.dumps(recent_tweets, indent=2)}

Words to avoid in the tweet:

{words_to_avoid_str}

Please generate the tweet following the system prompt. Ensure the tweet is less than 140 characters and matches the specified length: **{selected_length}**.
"""

        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()}
            ],
            max_tokens=100,
            temperature=1,
            n=1,
        )

        # Extract tweet content
        tweet_content = completion.choices[0].message.content.strip()
        # Ensure the tweet is under 140 characters
        tweet_content = tweet_content[:140]

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

def get_random_idea_tweet_topic():
    import random

    # List of 100 simple but profound ideas
    ideas = [
        "Practice gratitude daily: Reflect on what you're thankful for to foster positivity.",
        "Live in the present moment: Focus on the here and now to reduce anxiety and stress.",
        "Treat others as you wish to be treated: The Golden Rule enhances relationships.",
        "Learn to forgive: Holding onto anger only hurts you.",
        "Prioritize relationships: Invest time in family and friends for deeper connections.",
        "Pursue your passions: Engage in activities that excite you to bring fulfillment.",
        "Take care of your body: Regular exercise and good nutrition boost mood and energy.",
        "Listen more than you speak: Understanding others improves communication.",
        "Embrace failure as a learning opportunity: Mistakes are steps toward growth.",
        "Set achievable goals: Having direction gives purpose.",
        "Simplify your life: Declutter possessions and commitments to reduce stress.",
        "Practice kindness: Small acts can make a big difference.",
        "Be yourself: Authenticity leads to genuine happiness.",
        "Learn to say no: Protect your time and energy.",
        "Cultivate mindfulness: Meditation enhances awareness and peace.",
        "Value experiences over things: Memories bring lasting joy.",
        "Nurture curiosity: Lifelong learning keeps life interesting.",
        "Accept what you cannot change: Focus on what you can control.",
        "Get enough sleep: Rest is essential for well-being.",
        "Smile more: It can improve your mood and others'.",
        "Spend time in nature: It can be healing and rejuvenating.",
        "Practice self-compassion: Treat yourself kindly during hardships.",
        "Limit screen time: Disconnect to reconnect with real life.",
        "Volunteer or help others: Giving back fosters happiness.",
        "Be open to new perspectives: Understanding others enriches your worldview.",
        "Invest in personal growth: Read, learn, and develop skills.",
        "Keep a journal: Writing thoughts can clarify emotions.",
        "Celebrate small victories: Acknowledge progress to stay motivated.",
        "Practice deep breathing: It reduces stress and centers you.",
        "Surround yourself with positive people: Influence matters.",
        "Live within your means: Financial stability reduces stress.",
        "Trust your intuition: Your gut feeling often guides you well.",
        "Practice patience: Good things often take time.",
        "Focus on solutions, not problems: This mindset fosters progress.",
        "Laugh often: Humor lightens life's burdens.",
        "Don't compare yourself to others: Focus on your own journey.",
        "Be honest with yourself and others: Integrity builds trust.",
        "Learn from criticism: Feedback can be valuable.",
        "Travel when possible: Exposure to new cultures broadens horizons.",
        "Maintain a work-life balance: Avoid burnout.",
        "Express love and appreciation: Let people know you care.",
        "Stay hydrated: Water is vital for health.",
        "Embrace change: It's the only constant in life.",
        "Be proactive, not reactive: Take charge of your actions.",
        "Cherish the simple things: Find joy in everyday moments.",
        "Practice active listening: Fully engage in conversations.",
        "Cultivate resilience: Bounce back from setbacks.",
        "Manage stress healthily: Find coping strategies that work for you.",
        "Be generous: Sharing brings satisfaction.",
        "Pursue continuous improvement: Strive to be better each day.",
        "Learn to let go: Release grudges and negative feelings.",
        "Keep promises: Reliability strengthens relationships.",
        "Be adaptable: Flexibility helps navigate life's changes.",
        "Prioritize self-care: Taking care of yourself enables you to help others.",
        "Seek feedback: It can help you grow.",
        "Develop empathy: Understand others' feelings.",
        "Plan but be flexible: Prepare but adapt as needed.",
        "Take responsibility for your actions: Accountability fosters respect.",
        "Appreciate art and beauty: It enriches the soul.",
        "Stay informed but not overwhelmed: Balance awareness with well-being.",
        "Practice gratitude in adversity: Find lessons in challenges.",
        "Value quality over quantity: In possessions and relationships.",
        "Communicate clearly: It prevents misunderstandings.",
        "Set boundaries: Protect your emotional space.",
        "Be open to love: Allow yourself to form deep connections.",
        "Don't dwell on the past: Learn and move forward.",
        "Exercise your mind: Puzzles, reading, and learning keep it sharp.",
        "Prioritize tasks: Focus on what's important, not just urgent.",
        "Share your knowledge: Teaching others reinforces your learning.",
        "Practice humility: Recognize your limitations.",
        "Be optimistic: A positive outlook improves outcomes.",
        "Reflect regularly: Self-examination promotes growth.",
        "Value diversity: Embrace differences in others.",
        "Be consistent: Steady effort yields results.",
        "Practice self-discipline: It leads to greater freedom.",
        "Enjoy solitude: Time alone can rejuvenate.",
        "Focus on solutions: Problem-solving empowers you.",
        "Celebrate others' successes: Be happy for others.",
        "Keep an open mind: New ideas can enhance life.",
        "Be grateful for what you have: Contentment brings peace.",
        "Listen to your body: It signals your needs.",
        "Develop a personal philosophy: It guides your decisions.",
        "Seek balance in all things: Moderation is key.",
        "Be proactive about health: Preventive care is better than reactive.",
        "Invest in experiences: They enrich your life.",
        "Respect nature: Environmental stewardship benefits all.",
        "Practice fair judgment: Avoid jumping to conclusions.",
        "Engage in creative activities: They stimulate the mind.",
        "Build a supportive community: Mutual support enhances life.",
        "Take calculated risks: They can lead to growth.",
        "Appreciate the journey: Life is about the process, not just the destination.",
        "Be a good role model: Influence others positively.",
        "Forgive yourself: Don't be overly self-critical.",
        "Embrace lifelong learning: Knowledge empowers you.",
        "Recognize that happiness is a choice: Attitude matters.",
        "Don't take things personally: Others' actions often aren't about you.",
        "Live with integrity: Align your actions with your values.",
        "Foster independence: Relying on yourself builds confidence.",
        "Be aware of your impact: Consider how your actions affect others.",
        "Remember that change starts with you: Personal transformation influences the world."
    ]

    # List of Types of Tweets
    types_of_tweets = [
        "Whimsical Observations",
        "Short Fairy Tales",
        "Encouragement and Wisdom",
        "Playful Humor and Derpiness",
        "Reflections and Gratitude",
        "Curiosity and Questions",
        "Storytelling and Mini-Narratives",
        "Puns and Wordplay",
        "Mysterious Musings",
        "Meta and Self-Referential"
    ]

    # List of Tweet Lengths
    tweet_lengths = [
        "super short (3-7 words)",
        "medium (one short sentence)",
        "long (two sentences)"
    ]

    # Raw Topics List with Subtopics
    topics_raw = [
        "Nature: sunbeams, clouds, rain, trees, mushrooms, flowers, stars, wind, rivers, puddles, seasons, grass, leaves, mountains, forests, oceans",
        "Animals: rhinos, birds, butterflies, ants, squirrels, snails, cats, rabbits, foxes, fireflies, hedgehogs",
        "Weather: storms, rainbows, lightning, snow, dew, fog, sunshine",
        "Identity and Growth: wobbling, learning, twirling, growing, self-discovery, potential",
        "Gratitude: friendships, kindness, connections, support, followers",
        "Adventures: exploration, chasing, tiny journeys, trying new things",
        "Invisible Forces: air, gravity, time, echoes, feelings",
        "Human Habits: technology, devices, glowing rectangles, objects like umbrellas, shoes, teacups",
        "Food and Recipes: imaginary meals, snacks, magical ingredients, sharing food",
        "Time: mornings, sunsets, nights, fleeting moments, past life musings",
        "Dreams: sleep adventures, dreamscapes, nighttime wonder",
        "Collaboration and Teamwork: helping others, shared efforts, community",
        "Past Life Speculations: being a cloud, a puddle, a pebble, something magical",
        "Silly Practical Advice: whimsical guidance, playful 'rules' for life",
        "Observations of Others: interpreting behaviors, celebrating uniqueness",
        "Subtle Lessons: life lessons hidden in whimsy, quiet reflections",
        "Playful Bragging: self-aware humor, wobbly accomplishments",
        "Gratitude and Appreciation: reflection on growth, celebration of community"
    ]

    # Parsing the Topics into a Dictionary
    topics = {}
    for item in topics_raw:
        if ':' in item:
            main_topic, subtopics = item.split(':', 1)
            main_topic = main_topic.strip()
            subtopics_list = [subtopic.strip() for subtopic in subtopics.split(',')]
            topics[main_topic] = subtopics_list
        else:
            topics[item.strip()] = []

    # Randomly select an idea
    selected_idea = random.choice(ideas)

    # Randomly select a type of tweet
    selected_tweet_type = random.choice(types_of_tweets)

    # Randomly select a tweet length
    selected_tweet_length = random.choice(tweet_lengths)

    # Randomly select a main topic and a subtopic (if available)
    selected_main_topic = random.choice(list(topics.keys()))
    subtopics = topics[selected_main_topic]
    if subtopics:
        selected_subtopic = random.choice(subtopics)
    else:
        selected_subtopic = None

    # Return the selected items as a dictionary
    return {
        'idea': selected_idea,
        'type_of_tweet': selected_tweet_type,
        'topic': selected_main_topic,
        'subtopic': selected_subtopic,
        'tweet_length': selected_tweet_length
    }

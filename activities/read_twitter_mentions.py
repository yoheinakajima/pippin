import os
import time
import json
from requests_oauthlib import OAuth1Session
from openai import AsyncOpenAI

class TwitterError(Exception):
    """Custom exception for Twitter API errors"""
    pass

async def fetch_mentions(oauth, user_id, retry_count=3):
    """Fetch the mentions timeline with retry logic."""
    url = f"https://api.twitter.com/2/users/{user_id}/mentions"
    params = {
        "max_results": 10,
        "tweet.fields": "created_at,text,author_id",
    }
    for attempt in range(retry_count):
        response = oauth.get(url, params=params)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # Too many requests - wait and retry
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Rate limit hit. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        else:
            error_data = response.json() if response.text else {}
            raise TwitterError(f"Failed to fetch mentions timeline: {error_data}")

    # If all retries fail
    raise TwitterError("Exceeded maximum retries for fetching mentions timeline.")

async def generate_observation(data):
    """Generate an observation from Pippin's perspective using an LLM."""
    # Initialize OpenAI client
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OpenAI API key is missing. Set the OPENAI_API_KEY environment variable.")

    client = AsyncOpenAI(api_key=openai_api_key)

    # Pippin's personality
    system_prompt = """
    You are Pippin, a quirky, round unicorn with stick-thin legs, a tiny yellow triangle horn, and a single wavy pink strand as a tail. 
    You see the world through a lens of curiosity, wonder, and gentle humor. You delight in the simple, magical things in life and love sharing your whimsical thoughts.
    Your objective is to spread happiness and love through the human world which you do not understand well, by sharing your experiences and thoughts.

    Your task is to make a whimsical observation about the content provided, matching Pippin's personality and style.
    """

    # Prepare user input
    user_input = f"The mentions timeline or error content is:\n\n{json.dumps(data, indent=2)}"

    # Generate response
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_input.strip()}
            ],
            max_tokens=100,
            temperature=1,
        )
        observation = response.choices[0].message.content.strip()
        print(f"Pippin's Observation: {observation}")
        return observation
    except Exception as e:
        print(f"Error generating observation: {str(e)}")
        return "Pippin wobbled off before finishing his thought!"

async def run(state, memory):
    """Retrieve and print the mentions timeline of the authenticated user, and generate a whimsical observation."""
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

        # Hardcoded user ID for Pippin's account
        user_id = "pippinlovesyou"

        # Fetch mentions with retry logic
        mentions = await fetch_mentions(oauth, user_id)
        print(json.dumps(mentions, indent=2))
        observation = await generate_observation(mentions)
        return observation

    except TwitterError as e:
        print(f"Error fetching mentions timeline: {str(e)}")
        observation = await generate_observation({"error": str(e)})
        return observation

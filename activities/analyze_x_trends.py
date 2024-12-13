import asyncio
import os
import json
import logging
from typing import List, Dict

from requests_oauthlib import OAuth1Session
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file (if using one)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)  # Change to DEBUG for more detailed logs
logger = logging.getLogger(__name__)

# Constants
PERSONALIZED_TRENDS_URL = "https://api.twitter.com/2/users/{id}/personalized_trends"  # Replace {id} with actual user ID
MAX_TRENDS = 50  # Maximum number of trends to fetch

class TrendFetchError(Exception):
    """Custom exception for errors while fetching trends from Twitter API."""
    pass

class LLMGenerationError(Exception):
    """Custom exception for errors during LLM generation."""
    pass

async def fetch_personalized_trends_oauth1(
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
    user_id: str
) -> List[Dict[str, any]]:
    """
    Fetches personalized trends for a specific user from Twitter API v2 using OAuth 1.0a.

    Args:
        api_key (str): Twitter API Key.
        api_secret (str): Twitter API Key Secret.
        access_token (str): Twitter Access Token.
        access_token_secret (str): Twitter Access Token Secret.
        user_id (str): The Twitter User ID for whom to fetch personalized trends.

    Returns:
        List[Dict[str, any]]: A list of personalized trends with their names and tweet counts.

    Raises:
        TrendFetchError: If there's an issue fetching or parsing the trends.
    """
    try:
        # Create OAuth1 session
        oauth = OAuth1Session(
            client_key=api_key,
            client_secret=api_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

        # Construct the personalized trends URL with the user ID
        url = PERSONALIZED_TRENDS_URL.format(id=user_id)

        # Make the GET request to fetch personalized trends
        response = oauth.get(url)

        if response.status_code != 200:
            error_data = response.json() if response.text else {}
            logger.error(f"Failed to fetch personalized trends: {response.status_code} {error_data}")
            raise TrendFetchError(f"Failed to fetch personalized trends: {response.status_code} {error_data}")

        data = response.json()
        logger.debug(f"Raw response data: {json.dumps(data, indent=2)}")  # For debugging

        trends = data.get('data', [])
        if not trends:
            logger.warning("No personalized trends data found in the response.")
            return []

        # Limit the number of trends to MAX_TRENDS
        trends = trends[:MAX_TRENDS]

        # Validate trend data
        validated_trends = []
        for trend in trends:
            trend_name = trend.get('name')
            tweet_count = trend.get('tweet_volume') if trend.get('tweet_volume') is not None else 0
            if trend_name:
                validated_trends.append({
                    'trend_name': trend_name,
                    'tweet_count': tweet_count
                })

        logger.info(f"Fetched {len(validated_trends)} personalized trends.")
        return validated_trends

    except Exception as e:
        logger.error(f"Unexpected error while fetching personalized trends: {e}")
        raise TrendFetchError(f"Unexpected error: {e}") from e

async def generate_trend_thoughts(trends: List[Dict[str, any]], openai_api_key: str) -> str:
    """
    Generates thoughts on the provided trends using OpenAI's LLM.

    Args:
        trends (List[Dict[str, any]]): A list of trends with their names and tweet counts.
        openai_api_key (str): The OpenAI API key.

    Returns:
        str: Generated thoughts on the trends.

    Raises:
        LLMGenerationError: If there's an issue generating the thoughts.
    """
    openai_client = AsyncOpenAI(api_key=openai_api_key)

    try:
        # Prepare the trends summary
        trends_summary = "\n".join([
            f"- **{trend['trend_name']}**: {trend['tweet_count']} tweets"
            for trend in trends
        ])

        system_prompt = (
            "You are a knowledgeable analyst who provides insightful thoughts on current social media trends. "
            "Analyze the following list of trends and provide your thoughts on what they indicate about current societal interests and behaviors."
        )

        user_prompt = (
            f"Here are the current personalized trends on Twitter:\n\n{trends_summary}\n\n"
            "Please provide your detailed thoughts and analysis on these trends."
        )

        # Generate the completion using OpenAI's GPT-4
        completion = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.7,
            n=1,
            stop=None,
        )

        thoughts = completion.choices[0].message.content.strip()
        logger.info("Successfully generated thoughts on trends.")
        return thoughts

    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise LLMGenerationError(f"OpenAI API error: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during LLM generation: {e}")
        raise LLMGenerationError(f"Unexpected error: {e}") from e

async def run(state=None, memory=None):
    """
    Main asynchronous function to fetch personalized trends and generate thoughts on them.

    Args:
        state: Optional state parameter (unused in this script).
        memory: Optional memory interface (unused in this script).

    Returns:
        str: Generated thoughts on the current trends.
    """
    # Retrieve environment variables for OAuth1.0a
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    # Retrieve OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Retrieve the Twitter User ID
    user_id = os.getenv("TWITTER_USER_ID")  # Ensure this is set in your .env

    # Validate credentials
    if not all([api_key, api_secret, access_token, access_token_secret, user_id]):
        logger.error("Missing required Twitter OAuth1.0a credentials or User ID.")
        return "Error: Missing Twitter OAuth1.0a credentials or User ID."

    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set.")
        return "Error: Missing OpenAI API key."

    try:
        # Fetch personalized trends from Twitter API using OAuth1.0a
        trends = await fetch_personalized_trends_oauth1(api_key, api_secret, access_token, access_token_secret, user_id)

        if not trends:
            logger.warning("No personalized trends fetched. Exiting.")
            return "No current personalized trends available to analyze."

        # Generate thoughts on the fetched trends using LLM
        thoughts = await generate_trend_thoughts(trends, openai_api_key)

        # Optionally, you can store the thoughts in memory or a database here
        if memory:
            await memory.store_memory(
                content=thoughts,
                activity='analyze_trends',
                source='LLM'
            )

        # Log or print the generated thoughts
        logger.info("Generated Thoughts on Personalized Trends:")
        logger.info(thoughts)

        return thoughts

    except TrendFetchError as e:
        logger.error(f"Failed to fetch personalized trends: {e}")
        return f"Error fetching personalized trends: {e}"
    except LLMGenerationError as e:
        logger.error(f"Failed to generate thoughts: {e}")
        return f"Error generating thoughts: {e}"
    except Exception as e:
        logger.error(f"Unexpected error in run function: {e}")
        return "An unexpected error occurred while analyzing trends."

if __name__ == "__main__":
    # For testing purposes, run the async run function and print the result
    result = asyncio.run(run())
    print("\nGenerated Thoughts on Personalized Trends:\n")
    print(result)

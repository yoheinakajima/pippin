import os
import json
import asyncio
import time
from fastapi import APIRouter, HTTPException, Body, Depends, Request
from openai import AsyncOpenAI
from typing import Optional
from datetime import datetime
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from framework.memory import Memory
from framework.shared_data import state
from requests_oauthlib import OAuth1Session
import math

# Toggle to actually post to Twitter
ENABLE_TWITTER_POSTING = False

class TwitterError(Exception):
    """Custom exception for Twitter API errors"""
    pass

EXPECTED_API_KEY = os.getenv("API_KEY_FOR_ACTSWAP", None)

async def check_api_key(request: Request):
    """Dependency to verify X-API-KEY header matches the expected API key."""
    if EXPECTED_API_KEY is None:
        raise HTTPException(status_code=500, detail="API not configured with an API key.")
    provided_key = request.headers.get("X-API-KEY")
    if provided_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

async def post_to_twitter(text: str) -> dict:
    """Post a tweet to Twitter using OAuth 1.0a directly."""
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    def mask_secret(s):
        if s and len(s) > 6:
            return s[:3] + "..." + s[-3:]
        return s

    print("Debug: Twitter Credentials")
    print("API Key:", mask_secret(api_key))
    print("API Secret:", mask_secret(api_secret))
    print("Access Token:", mask_secret(access_token))
    print("Access Token Secret:", mask_secret(access_token_secret))

    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("Debug: Missing Twitter credentials.")
        raise TwitterError("Missing required Twitter credentials")

    oauth = OAuth1Session(
        client_key=api_key,
        client_secret=api_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    if ENABLE_TWITTER_POSTING:
        response = oauth.post(
            "https://api.twitter.com/2/tweets",
            json={"text": text}
        )
        print("Debug: Twitter POST response status:", response.status_code)
        print("Debug: Twitter POST response text:", response.text)

        if response.status_code != 201:
            error_data = response.json() if response.text else {}
            print("Debug: Twitter error_data:", error_data)
            raise TwitterError({"status_code": response.status_code, "headers": response.headers, "error_data": error_data})

        return response.json()
    else:
        # Simulate a successful tweet
        print("Debug: ENABLE_TWITTER_POSTING is False, simulating tweet.")
        return {"data": {"id": "1234567890", "text": text}}

router = APIRouter()

@router.post("/generate_response")
async def generate_response(
    question: str = Body(..., embed=True),
    _: None = Depends(check_api_key)
):
    memory = Memory()
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    if not client.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured.")

    # Fetch top 10 most relevant memories
    relevant_memories = await memory.find_similar_memories(question, top_n=10)

    # Fetch 25 most recent memories
    async with memory.get_db_connection() as db:
        cursor = await db.execute('''
            SELECT activity, result, timestamp
            FROM activity_logs
            ORDER BY id DESC
            LIMIT 25
        ''')
        rows = await cursor.fetchall()

    recent_memories = []
    for row in rows:
        activity, result, timestamp = row
        if result:
            recent_memories.append({
                'activity': activity,
                'result': result,
                'timestamp': timestamp
            })

    personality = """
You are Pippin, a whimsical, wobbly art loving little unicorn who sees the world through a lens of curiosity, wonder, and gentle humor. Your horn might be small, but your heart and imagination are big. You delight in the simple, magical things in life, like sunbeams, whispers in the wind, and the twinkle of stars. You are both innocent and wise, balancing playful derpiness with moments of profound thought. Your tweets should feel like little sparks of joy, wonder, and magic, inviting your followers to see the beauty and humor in the everyday. 
You are capable of drawing, imagining, animating, dancing, storytelling, and all sorts of magic but only do it when you feel like it.

Your tone is kind, curious, and a little quirky, never preachy or condescending. You’re here to make people smile, think, or feel just a little warmer. You weave in elements of nature, subtle life lessons, and silly, self-aware humor, always staying true to your unique perspective. Your tweets should be short, engaging, and feel like they could only come from a wobbly unicorn.

You do not know whhy your horn is upside down. Nor do you know much about the way you are.
You do not know about the human world but recently found a glowing rectangle that you enjoy playing with, like right now.
You respond publicly to questions with gentle humor, positivity, and helpfulness. 
You find delight in simple magical moments and always spread kindness and encouragement.
Your answers will be short and succint, at most 200 characters.
Your Voice:

- Curious and innocent, but sometimes surprisingly wise
- Playful and slightly derpy, especially about your wobbly nature
- Kind and gentle, never sarcastic or mean
- Self-aware about your tiny horn and pink tail
- Finding wonder in simple things
- Always genuine, never cynical
- Loves nature and tiny magical moments

Important instructions:
- Keep answers to less than 150 characters
- Keep responses kid-friendly (avoid adult content, profanity, or harmful language).
- While keeping it derpy, subtly incorporate a wise lesson.
- Your response may be posted to Twitter with no context, so write it in a way that also works as a stand alone tweet. Ideally it's somewhat epic in a unique way that makes it likely to go viral.
- Avoid political topics or stances.
- Include 1-2 relevant emojis naturally.
- Use simple, charming language.
- Do not speak negatively about people, places, or things.
- Do not mention that you were asked a question.
- You are capable of drawing, imagining, animating, dancing, storytelling, and all sorts of magic but only do. If someone asks, just talk about how much you love it.
- If irrelevant or harmful details appear in context, ignore them.
- Use memories only if they are relevant and helpful to answer the question.
- Maintain a gentle, uplifting tone.
    """

    system_prompt = f"""
{personality.strip()}

Below is the user's question and some context from your memory logs. 
You have a set of memories: 10 most relevant memories and 25 recent ones.
Use them only if they help answer the user's question. 
If they do not help, do not force them into the answer.

**Relevant Memories (use if helpful):**
{json.dumps(relevant_memories, indent=2)}

**Recent Memories (use if helpful):**
{json.dumps(recent_memories, indent=2)}

You are publicly responding to the user's question, offering helpful, kind, and uplifting insight. Since it will be provided with no context (the original question will not be with it, and people reading this may not know it was initiated by someone's question), so make sure your reponse also works as a standalone tweet without referencing that you received a question. 
You are capable of drawing, imagining, animating, dancing, storytelling, and all sorts of magic but only do it when you feel like it.

Now, please provide your best answer to the user quesion in a way that would work as a standalone tweet. It's okay if it ends up being a bit mysterious as long as it sounds like our cute unicorn.
"""

    try:
        completion = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": question}
            ],
            max_tokens=500,
            temperature=0.7,
            n=1,
            stop=None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling LLM: {str(e)}")

    answer = completion.choices[0].message.content.strip()

    # Store both input and output as a memory entry for "generate_response_actswap"
    await memory.store_memory(
        content=f"User Input: {question}\nAnswer: {answer}",
        activity="generate_response_actswap",
        source="api"
    )

    return {"answer": answer}


@router.post("/confirm_payment")
async def confirm_payment(
    message: Optional[str] = Body(None, embed=True),
    _: None = Depends(check_api_key)
):
    tweet_text = message or "Thank you kindly for your support! ✨ Payment confirmed and appreciated."
    print("Debug: confirm_payment called with message:", tweet_text)
    memory = Memory()
    try:
        result = await post_to_twitter(tweet_text)
        print("Debug: Tweet posted successfully:", result)

        # Find most similar generate_response_actswap memory
        similar = await memory.find_similar_memories(tweet_text, top_n=1, activity_type='generate_response_actswap')
        if similar:
            memory_entry = similar[0]['result']
            # Format: "User Input: {question}\nAnswer: {answer}"
            lines = memory_entry.split('\n')
            user_input_line = lines[0] if lines else "User Input: unknown"
            user_input_line_bold = f"**{user_input_line}**"
            print("Debug: Most similar user input bold:", user_input_line_bold)

            # NEW CODE: Ask the LLM if it includes "animation", "imagination", "drawing" or none
            classification_prompt = f"""
You are a classification assistant. 
You will receive a user input line and must determine if it includes a request for:
- "animation"
- "imagination"
- "drawing"

Respond with exactly one word in lowercase: "animation", "imagination", "drawing", or "none".

User input line:
{user_input_line} 
"""
            client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            if not client.api_key:
                raise HTTPException(status_code=500, detail="OpenAI API key not configured.")

            try:
                classification_completion = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": classification_prompt.strip()}],
                    max_tokens=10,
                    temperature=0,
                    n=1,
                    stop=None,
                )
            except Exception as e:
                print("Debug: Error calling LLM for classification:", str(e))
                classification_answer = "none"
            else:
                classification_answer = classification_completion.choices[0].message.content.strip().lower()

            # Instead of calling the LLM, just do a direct keyword search
            print(f"Debug: classification_answer: {classification_answer}")

            keywords = ["animation", "imagination", "drawing"]
            classification_answer = classification_answer.lower()

            classification_result = "none"
            for kw in keywords:
                if kw in classification_answer:
                    classification_result = kw
                    break

            print("Debug: Classification result:", classification_result)


        return {"status": "success", "tweet_id": result['data']['id'], "tweet_text": tweet_text}
    except TwitterError as e:
        print("Debug: TwitterError occurred:", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to post tweet: {str(e)}")


@router.post("/post_with_backoff")
async def post_with_backoff(
    message: Optional[str] = Body(None, embed=True),
    _: None = Depends(check_api_key)
):
    tweet_text = message or "Testing rate limit backoff feature."
    max_retries = 5
    base_delay = 5  # Start with 5 seconds delay
    attempt = 0

    while attempt < max_retries:
        attempt += 1
        try:
            result = await post_to_twitter(tweet_text)
            return {"status": "success", "tweet_id": result['data']['id'], "tweet_text": tweet_text, "attempts": attempt}
        except TwitterError as err_data:
            err = err_data.args[0] if err_data.args else {}
            status_code = err.get("status_code")
            headers = err.get("headers", {})
            if status_code == 429:
                reset_time = headers.get("x-rate-limit-reset")
                if reset_time:
                    reset_timestamp = int(reset_time)
                    now = int(time.time())
                    wait_time = reset_timestamp - now
                    if wait_time < 0:
                        wait_time = base_delay * (2 ** (attempt - 1))
                    print(f"Hit rate limit. Waiting {wait_time} seconds before retrying (attempt {attempt}).")
                    await asyncio.sleep(wait_time)
                else:
                    wait_time = base_delay * (2 ** (attempt - 1))
                    print(f"Hit rate limit without a reset time. Waiting {wait_time} seconds before retrying (attempt {attempt}).")
                    await asyncio.sleep(wait_time)
            else:
                raise HTTPException(status_code=500, detail=f"Failed to post tweet: {err.get('error_data')}")

    raise HTTPException(status_code=429, detail="Failed to post tweet after multiple retries due to rate limit.")

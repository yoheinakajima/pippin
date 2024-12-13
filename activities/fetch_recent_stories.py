# activities/fetch_recent_songs.py
import asyncio
import os
import base64
import requests
from datetime import datetime

async def run(state, memory):
    """
    Activity: Fetch Recent Songs from Spotify Show
    Description: Retrieves the most recent songs (episodes) from a specified Spotify show and stores them in Pippin's memory.
    """

    # Spotify credentials from environment variables
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

    if not client_id or not client_secret:
        result_message = "Spotify credentials are not set. Please configure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
        await memory.store_memory(content=result_message, activity='fetch_recent_songs')
        return result_message

    # Encode client credentials
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    # Request access token
    token_url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials"
    }

    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()
        access_token = response.json().get('access_token')
    except requests.exceptions.RequestException as e:
        result_message = f"Failed to obtain access token: {e}"
        await memory.store_memory(content=result_message, activity='fetch_recent_songs')
        return result_message

    if not access_token:
        result_message = "Access token not found in the response."
        await memory.store_memory(content=result_message, activity='fetch_recent_songs')
        return result_message

    # Fetch recent episodes
    show_id = "7bSjEIuLl16wJOXptkvhrY"
    episodes_url = f"https://api.spotify.com/v1/shows/{show_id}/episodes"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "limit": 5,  # Fetch the 5 most recent episodes
        "market": "US"  # Specify market if needed
    }

    try:
        response = requests.get(episodes_url, headers=headers, params=params)
        response.raise_for_status()
        episodes = response.json().get('items', [])
    except requests.exceptions.RequestException as e:
        result_message = f"Failed to fetch episodes: {e}"
        await memory.store_memory(content=result_message, activity='fetch_recent_songs')
        return result_message

    if not episodes:
        result_message = "No recent episodes found for the specified show."
        await memory.store_memory(content=result_message, activity='fetch_recent_songs')
        return result_message

    # Process and store episodes
    song_details = []
    for episode in episodes:
        song_name = episode.get('name')
        release_date = episode.get('release_date')
        external_url = episode.get('external_urls', {}).get('spotify')

        # Convert release_date to a readable format
        try:
            release_date_obj = datetime.strptime(release_date, "%Y-%m-%d")
            formatted_release_date = release_date_obj.strftime("%B %d, %Y")
        except ValueError:
            formatted_release_date = release_date

        song_info = f"**{song_name}** released on {formatted_release_date}. Listen here: {external_url}"
        song_details.append(song_info)

    # Create a summary message
    songs_summary = "\n".join(song_details)
    result_message = f"Pippin has discovered the latest songs from the show:\n{songs_summary}"

    # Store in memory
    await memory.store_memory(content=result_message, activity='fetch_recent_songs')

    # Optionally, update Pippin's state or tweet about the new songs
    # Example: state.happiness += 10
    state.happiness = min(state.happiness + 10, 100)
    await memory.store_memory(content="Pippin feels happy about the new stories!", activity='update_happiness')

    return result_message

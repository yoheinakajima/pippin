# activities/template_activity.py
import asyncio
import random
import json

async def run(state, memory):
    """
    Activity: Template Activity
    Description: Template showing memory search capabilities.
    """
    # Simulate activity duration
    duration = random.randint(1, 3)
    await asyncio.sleep(duration)

    # Update state
    state.energy = max(state.energy - 10, 0)
    state.happiness = min(state.happiness + 5, 100)
    state.xp += 5

    # Define a search query
    search_query = "I am feeling energetic and happy"

    # Find similar memories
    similar_memories = await memory.find_similar_memories(
        text=search_query,
        top_n=3,  # Get top 3 similar memories
        activity_type=None,  # Search all activity types
        source=None  # Search all sources
    )

    # Format the similar memories for display
    memory_summary = []
    for mem in similar_memories:
        memory_summary.append({
            'id': mem['id'],
            'activity': mem['activity'],
            'similarity_result': mem['result']
        })

    # Create result message
    result_data = {
        'search_query': search_query,
        'similar_memories': memory_summary,
        'total_found': len(memory_summary)
    }

    # Store activity with detailed result
    entry = {
        'activity': 'template_activity',
        'result': json.dumps(result_data, indent=2),  # Pretty print the JSON
        'state_changes': {
            'energy': -10,
            'happiness': 5,
            'xp': 5
        },
        'final_state': {
            'energy': state.energy,
            'happiness': state.happiness,
            'xp': state.xp
        }
    }

    await memory.store_activity(entry)

    # Return the activity outcome
    return f"Found {len(memory_summary)} similar memories to query: '{search_query}'"
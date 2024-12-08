import asyncio
import os
import json
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import Dict

class WalkResult(BaseModel):
    """Schema for walk activity results"""
    description: str = Field(..., description="Description of the walk experience")
    duration_minutes: int = Field(..., description="Duration of walk in minutes", ge=1, le=10)
    state_changes: Dict[str, int] = Field(
        ...,
        description="Changes to energy, happiness, and xp",
        example={
            "energy": -10,
            "happiness": 10,
            "xp": 4
        }
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "description": "Pippin bounced along the mossy path, discovering a family of glowing mushrooms",
                "duration_minutes": 5,
                "state_changes": {
                    "energy": -10,
                    "happiness": 10,
                    "xp": 4
                }
            }]
        }
    }

async def run(state, memory):
    """
    Activity: Take a Walk
    Description: Pippin goes on a whimsical walk in Wobbly Woods, encountering various magical creatures and finding joy in simple things.
    """
    # Initialize OpenAI client
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    if not client.api_key:
        print("OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
        return

    # Fetch recent walk experiences to avoid repetition
    async with memory.get_db_connection() as db:
        cursor = await db.execute('''
            SELECT result 
            FROM activity_logs 
            WHERE activity = 'take_walk' 
            ORDER BY id DESC 
            LIMIT 3
        ''')
        rows = await cursor.fetchall()
        recent_walks = [row[0] for row in rows if row[0]]

    try:
        function_schema = {
            "name": "record_walk",
            "description": "Record the details of Pippin's walk",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description of the walk experience"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration of walk in minutes",
                        "minimum": 1,
                        "maximum": 10
                    },
                    "state_changes": {
                        "type": "object",
                        "description": "Changes to energy, happiness, and xp",
                        "properties": {
                            "energy": {
                                "type": "integer",
                                "minimum": -15,
                                "maximum": -5,
                                "description": "Energy change during walk"
                            },
                            "happiness": {
                                "type": "integer",
                                "minimum": 5,
                                "maximum": 15,
                                "description": "Happiness change during walk"
                            },
                            "xp": {
                                "type": "integer",
                                "minimum": 2,
                                "maximum": 6,
                                "description": "Experience points gained during walk"
                            }
                        },
                        "required": ["energy", "happiness", "xp"]
                    }
                },
                "required": ["description", "duration_minutes", "state_changes"]
            }
        }

        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """You are generating walk experiences for Pippin, a quirky, round unicorn 
                with stick-thin legs, a tiny yellow triangle horn, and a single wavy pink strand as a tail. 
                He lives in the magical Wobbly Woods and often goes on gentle adventures with his best friend Dot the ladybug.
                Generate a unique walk experience different from recent ones."""},
                {"role": "user", "content": f"""
                Generate a whimsical description of Pippin's walk today.

                Current state:
                - Energy: {state.energy} (walking makes Pippin tired but he enjoys it!)
                - Happiness: {state.happiness} (Pippin finds joy in little things)
                - XP: {state.xp} (Learning through gentle adventures)

                Recent walks (to avoid repetition):
                {json.dumps(recent_walks, indent=2)}
                """}
            ],
            functions=[function_schema],
            function_call={"name": "record_walk"}
        )

        # Parse the function call response
        function_args = json.loads(completion.choices[0].message.function_call.arguments)
        result = WalkResult(**function_args)

        # Extract values
        description = result.description
        print(description)
        duration = result.duration_minutes*10  # Convert to seconds and multiply by 10
        state_changes = result.state_changes

        # Simulate walk duration
        await asyncio.sleep(duration)

        # Apply state changes with bounds checking
        state.energy = max(state.energy + state_changes['energy'], 0)
        state.happiness = min(state.happiness + state_changes['happiness'], 100)
        state.xp += state_changes['xp']

        # Create memory content
        memory_content = {
            'description': description,
            'duration_minutes': result.duration_minutes,
            'state_changes': state_changes,
            'state_snapshot': {
                'energy': state.energy,
                'happiness': state.happiness,
                'xp': state.xp
            }
        }

        # Store memory
        await memory.store_memory(
            content=json.dumps(memory_content, indent=2),
            activity='take_a_walk',
            source='activity'
        )

        return description

    except Exception as e:
        print(f"Error during Pippin's walk: {str(e)}")
        return "Pippin got a bit wobbly and had to cut his walk short today."
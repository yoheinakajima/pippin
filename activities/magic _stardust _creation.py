# activities/magic_stardust_creation.py

import asyncio
import os
import json
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import Dict

class StardustResult(BaseModel):
    """Schema for Magic Stardust Creation activity results"""
    stardust: str = Field(..., description="Stardust created by Pippin")
    state_changes: Dict[str, int] = Field(
        ...,
        description="Changes to energy, happiness, and xp",
        example={
            "energy": -10,
            "happiness": 15,
            "xp": 3
        }
    )

    class Config:
        schema_extra = {
            "examples": [{
                "stardust": "A sparkling cluster of blue and green stardust, glittering with a soft light.",
                "state_changes": {
                    "energy": -10,
                    "happiness": 15,
                    "xp": 3
                }
            }]
        }

async def run(state, memory):
    """
    Activity: Magic Stardust Creation
    Description: Pippin uses his digital unicorn magic to create sparkling stardust. Users can choose the color and intensity of the stardust, and Pippin will weave them together to create a dazzling display.
    """
    # Initialize OpenAI client
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    if not client.api_key:
        error_message = "Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
        print(error_message)
        return error_message

    # Define the function schema for magic stardust creation
    function_schema = {
        "name": "record_stardust_creation",
        "description": "Record the details of Pippin's magic stardust creation activity",
        "parameters": {
            "type": "object",
            "properties": {
                "stardust": {
                    "type": "string",
                    "description": "Description of the stardust created by Pippin"
                },
                "state_changes": {
                    "type": "object",
                    "description": "Changes to energy, happiness, and xp",
                    "properties": {
                        "energy": {
                            "type": "integer",
                            "description": "Energy change after creating stardust",
                            "minimum": -20,
                            "maximum": 0
                        },
                        "happiness": {
                            "type": "integer",
                            "description": "Happiness change after creating stardust",
                            "minimum": 10,
                            "maximum": 25
                        },
                        "xp": {
                            "type": "integer",
                            "description": "Experience points gained after creating stardust",
                            "minimum": 2,
                            "maximum": 5
                        }
                    },
                    "required": ["energy", "happiness", "xp"]
                }
            },
            "required": ["stardust", "state_changes"]
        }
    }

    try:
        # Create chat completion with function calling
        completion = await client.chat.completions.create(
            model="gpt-4",  # Ensure correct model name
            messages=[
                {"role": "user", "content": "Pippin, create a magnificent display of stardust today."}
            ],
            functions=[function_schema],
            function_call={"name": "record_stardust_creation"}  # Instruct the model to call the function
        )

        # Ensure that the response contains a function call
        if not completion.choices or not completion.choices[0].message.function_call:
            error_message = "Error: No function call found in the response."
            print(error_message)
            return error_message

        # Parse the function call response
        function_args = json.loads(completion.choices[0].message.function_call.arguments)
        result = StardustResult(**function_args)

        # Extract values
        stardust = result.stardust
        print(f"Created Stardust: {stardust}")
        state_changes = result.state_changes

        # Simulate stardust creation duration
        await asyncio.sleep(20)

        # Apply state changes with bounds checking
        state.energy = max(state.energy + state_changes['energy'], 0)
        state.happiness = min(state.happiness + state_changes['happiness'], 100)
        state.xp += state_changes['xp']

        # Create memory content
        memory_content = {
            'stardust': stardust,
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
            activity='magic_stardust_creation',
            source='activity'
        )

        return stardust

    except Exception as e:
        error_message = f"Error during Pippin's stardust creation: {str(e)}"
        print(error_message)
        return "Pippin got a bit wobbly and had to cut his stardust creation short today."

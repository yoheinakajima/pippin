import os
import re
import json
import time
import asyncio
from openai import AsyncOpenAI
import litellm
from PIL import Image
import io
import svglib.svglib
from reportlab.graphics import renderPM
from pathlib import Path

# Ensure static/images directory exists
IMAGES_DIR = Path("static/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

async def run(state, memory):
    """
    Activity: Draw
    Description: Pippin creates a whimsical illustration based on a recent memory.
    """
    try:
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not client.api_key:
            print("OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
            return "Pippin couldn't find his drawing supplies."

        # Fetch recent memories
        async with memory.get_db_connection() as db:
            cursor = await db.execute('''
                SELECT result 
                FROM activity_logs 
                WHERE activity != 'draw'
                ORDER BY id DESC 
                LIMIT 5
            ''')
            rows = await cursor.fetchall()
            recent_memories = [row[0] for row in rows if row[0]]

        if not recent_memories:
            return "Pippin couldn't find any memories to draw."

        # Select the most recent memory
        selected_memory = recent_memories[0]

        # Extract the scene to illustrate
        scene_response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "user", "content": f"""Given this memory, extract the most visually interesting moment that would make a good illustration:

                Memory: {selected_memory}

                Provide your response in this format:
                Scene: [brief description of the visual scene]
                Style: [suggested art style for the illustration]
                Key Elements: [comma-separated list of important visual elements]"""}
            ]
        )
        scene_info = scene_response.choices[0].message.content

        # Generate SVG using o1-mini
        svg_prompt = f"""Create a whimsical, cute SVG illustration based on this scene:
        {scene_info}

        Requirements:
        - Keep the SVG simple and clean
        - Use soft, friendly colors
        - Include a viewBox attribute
        - Make it suitable for a children's book illustration
        - Ensure the SVG is well-formed and complete

        Respond only with the SVG code."""

        svg_response = litellm.completion(
            model="o1-mini",
            messages=[{"content": svg_prompt, "role": "user"}]
        )
        svg_text = svg_response['choices'][0]['message']['content']

        # Extract SVG code
        svg_pattern = re.compile(r'<svg[\s\S]*?<\/svg>', re.IGNORECASE)
        svg_match = svg_pattern.search(svg_text)
        if not svg_match:
            return "Pippin's drawing came out a bit wobbly and unclear."

        svg_code = svg_match.group(0)

        # Save as JPEG
        timestamp = int(time.time())
        filename = f"pippin_drawing_{timestamp}.jpg"

        try:
            # First save SVG to a temporary file
            temp_svg = IMAGES_DIR / f"temp_{timestamp}.svg"
            with open(temp_svg, 'w') as f:
                f.write(svg_code)

            # Convert SVG to PNG using svglib
            drawing = svglib.svglib.svg2rlg(str(temp_svg))

            # Save as PNG first
            temp_png = IMAGES_DIR / f"temp_{timestamp}.png"
            renderPM.drawToFile(drawing, str(temp_png), fmt="PNG")

            # Convert PNG to JPEG using Pillow
            with Image.open(temp_png) as img:
                img = img.convert('RGB')
                filepath = IMAGES_DIR / filename
                img.save(filepath, 'JPEG', quality=90)

            # Clean up temporary files
            temp_svg.unlink(missing_ok=True)
            temp_png.unlink(missing_ok=True)

            web_path = f"images/{filename}"

        except Exception as e:
            print(f"Error saving image: {str(e)}")
            return "Pippin tried to save his drawing but got his hooves tangled."

        # Store the result
        result = {
            'original_memory': selected_memory,
            'scene_info': scene_info,
            'svg_code': svg_code,
            'image_path': web_path,
        }

        await memory.store_memory(
            content=json.dumps(result, indent=2),
            activity='draw',
            source='activity'
        )

        return f"Pippin made a drawing inspired by a recent memory! You can find it at {web_path}"

    except Exception as e:
        print(f"Error in draw activity: {str(e)}")
        return "Pippin's art supplies got a bit mixed up today."
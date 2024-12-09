import os
import re
import time
import random
from pathlib import Path
from PIL import Image
import cairosvg
import litellm
from openai import AsyncOpenAI
import asyncio

IMAGES_DIR = Path("static/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Base unicorn SVG (static)
BASE_UNICORN_SVG = """
<svg width="1000" height="1000" viewBox="0 0 1000 1000" xmlns="http://www.w3.org/2000/svg">
  <rect width="1000" height="1000" fill="#f0f8ff"></rect>
  <!-- Unicorn Body -->
  <path d="M320,600 Q240,480 320,360 Q400,240 560,280 Q720,320 640,480 Q600,640 400,640 Z" fill="#fff" stroke="#000" stroke-width="8"></path>
  <!-- Unicorn Neck and Head -->
  <path d="M560,280 Q600,240 640,220 Q680,200 700,240 Q720,280 680,320 Q640,340 600,320 Q560,300 560,280 Z" fill="#fff" stroke="#000" stroke-width="8"></path>
  <!-- Horn -->
  <polygon points="640,220 620,140 660,140" fill="#ffd700" stroke="#000" stroke-width="4"></polygon>
  <!-- Ears -->
  <path d="M660,180 Q664,160 640,172" fill="#fff" stroke="#000" stroke-width="4"></path>
  <path d="M680,180 Q684,160 660,172" fill="#fff" stroke="#000" stroke-width="4"></path>
  <!-- Eyes -->
  <circle cx="648" cy="240" r="12" fill="#000"></circle>
  <circle cx="632" cy="240" r="6" fill="#fff"></circle>
  <!-- Mane -->
  <path d="M620,220 Q600,240 620,260 Q600,280 620,300 Q600,320 620,340" stroke="#ff69b4" stroke-width="8" fill="none"></path>
  <path d="M640,220 Q620,240 640,260 Q620,280 640,300 Q620,320 640,340" stroke="#ff69b4" stroke-width="8" fill="none"></path>
  <!-- Legs -->
  <path d="M400,640 L400,760" stroke="#000" stroke-width="8"></path>
  <path d="M480,640 L480,760" stroke="#000" stroke-width="8"></path>
  <path d="M560,640 L560,760" stroke="#000" stroke-width="8"></path>
  <path d="M640,480 Q660,560 640,640" stroke="#000" stroke-width="8"></path>
  <!-- Tail -->
  <path d="M320,600 Q280,620 300,640 Q280,660 320,680" stroke="#ff69b4" stroke-width="8" fill="none"></path>
  <path d="M300,640 Q320,660 300,680" stroke="#ff69b4" stroke-width="8" fill="none"></path>
  <!-- Hooves -->
  <ellipse cx="400" cy="760" rx="20" ry="8" fill="#000"></ellipse>
  <ellipse cx="480" cy="760" rx="20" ry="8" fill="#000"></ellipse>
  <ellipse cx="560" cy="760" rx="20" ry="8" fill="#000"></ellipse>
  <ellipse cx="640" cy="640" rx="20" ry="8" fill="#000"></ellipse>
  <!-- Details on Body -->
  <path d="M360,480 Q380,440 400,480" stroke="#000" stroke-width="4" fill="none"></path>
  <path d="M440,520 Q460,480 480,520" stroke="#000" stroke-width="4" fill="none"></path>
</svg>
"""

async def generate_pippin_drawing(scene_description: str, api_key_openai: str, output_path: str = None) -> str:
    """
    Generate a whimsical drawing (JPEG) from a provided scene description, with dynamic use of the base unicorn SVG.
    """
    if not api_key_openai:
        print("OpenAI API key not found. Cannot generate drawing.")
        return None

    client = AsyncOpenAI(api_key=api_key_openai)

    # Decide whether to include the base unicorn SVG (50% probability)
    include_base_unicorn = random.choice([True, False])

    # Get scene info from GPT model
    system_msg = "You are an assistant that extracts the most visually interesting scene from a memory."
    user_msg = f"""Given this memory, extract the most visually interesting moment that would make a good illustration:

    Memory: {scene_description}

    Provide your response in this format:
    Scene: [brief description of the visual scene]
    Style: [suggested art style for the illustration]
    Key Elements: [comma-separated list of important visual elements]"""

    scene_response = await client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ]
    )
    scene_info = scene_response.choices[0].message.content.strip()

    # Generate SVG prompt
    if include_base_unicorn:
        svg_prompt = f"""You have a base unicorn SVG (no animations):

{BASE_UNICORN_SVG}

Update this SVG to incorporate the following scene and visual elements:
{scene_info}

Requirements:
- Retain unicorn structure from base SVG, but adjust his size, rotation, and location accordingly to the scene description.
- Add visual details based on the scene description.
- Include a viewBox="0 0 1000 1000".
- Use only solid colors, no gradients or filters.
- Ensure the SVG is well-formed and complete.
- Respond ONLY with the updated SVG code.
"""
    else:
        svg_prompt = f"""Create a whimsical SVG illustration based on this scene:
{scene_info}

Requirements:
- Do NOT include the base unicorn SVG.
- Add visual details based on the scene description.
- Include a viewBox="0 0 1000 1000".
- Use only solid colors, no gradients or filters.
- Ensure the SVG is well-formed and complete.
- Respond ONLY with the SVG code.
"""

    svg_response = litellm.completion(
        model="o1-mini",
        messages=[{"content": svg_prompt, "role": "user"}]
    )
    svg_text = svg_response['choices'][0]['message']['content']

    svg_pattern = re.compile(r'<svg[\s\S]*?<\/svg>', re.IGNORECASE)
    svg_match = svg_pattern.search(svg_text)
    if not svg_match:
        print("No valid SVG found in the response.")
        return None

    svg_code = svg_match.group(0)

    timestamp = int(time.time())
    if output_path is None:
        filename = f"pippin_drawing_{timestamp}.jpg"
        output_path = str(IMAGES_DIR / filename)
    else:
        output_path = str(IMAGES_DIR / output_path)

    temp_svg = IMAGES_DIR / f"temp_{timestamp}.svg"
    temp_png = IMAGES_DIR / f"temp_{timestamp}.png"

    # Save SVG
    with open(temp_svg, 'w') as f:
        f.write(svg_code)

    # Convert SVG to PNG
    cairosvg.svg2png(url=str(temp_svg), write_to=str(temp_png))

    # Convert PNG to JPEG using PIL
    with Image.open(temp_png) as img:
        img = img.convert('RGB')
        img.save(output_path, 'JPEG', quality=95)

    # Clean up
    temp_svg.unlink(missing_ok=True)
    temp_png.unlink(missing_ok=True)

    return output_path

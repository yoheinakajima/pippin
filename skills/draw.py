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
<svg width="250" height="250" viewBox="0 0 250 250" xmlns="http://www.w3.org/2000/svg">
  <!-- Unicorn Body -->
  <path d="M80,150 Q60,120 80,90 Q100,60 140,70 Q180,80 160,120 Q150,160 100,160 Z" fill="#fff" stroke="#000" stroke-width="2"></path>
  <!-- Unicorn Neck and Head -->
  <path d="M140,70 Q150,60 160,55 Q170,50 175,60 Q180,70 170,80 Q160,85 150,80 Q140,75 140,70 Z" fill="#fff" stroke="#000" stroke-width="2"></path>
  <!-- Horn -->
  <polygon points="160,55 155,35 165,35" fill="#ffd700" stroke="#000" stroke-width="1"></polygon>
  <!-- Ears -->
  <path d="M165,45 Q166,40 160,43" fill="#fff" stroke="#000" stroke-width="1"></path>
  <path d="M170,45 Q171,40 165,43" fill="#fff" stroke="#000" stroke-width="1"></path>
  <!-- Eyes -->
  <circle cx="162" cy="60" r="3" fill="#000"></circle>
  <circle cx="158" cy="60" r="1.5" fill="#fff"></circle>
  <!-- Mane -->
  <path d="M155,55 Q150,60 155,65 Q150,70 155,75 Q150,80 155,85" stroke="#ff69b4" stroke-width="2" fill="none"></path>
  <path d="M160,55 Q155,60 160,65 Q155,70 160,75 Q155,80 160,85" stroke="#ff69b4" stroke-width="2" fill="none"></path>
  <!-- Legs -->
  <path d="M100,160 L100,190" stroke="#000" stroke-width="2"></path>
  <path d="M120,160 L120,190" stroke="#000" stroke-width="2"></path>
  <path d="M140,160 L140,190" stroke="#000" stroke-width="2"></path>
  <path d="M160,120 Q165,140 160,160" stroke="#000" stroke-width="2"></path>
  <!-- Tail -->
  <path d="M80,150 Q70,155 75,160 Q70,165 80,170" stroke="#ff69b4" stroke-width="2" fill="none"></path>
  <path d="M75,160 Q80,165 75,170" stroke="#ff69b4" stroke-width="2" fill="none"></path>
  <!-- Hooves -->
  <ellipse cx="100" cy="190" rx="5" ry="2" fill="#000"></ellipse>
  <ellipse cx="120" cy="190" rx="5" ry="2" fill="#000"></ellipse>
  <ellipse cx="140" cy="190" rx="5" ry="2" fill="#000"></ellipse>
  <ellipse cx="160" cy="160" rx="5" ry="2" fill="#000"></ellipse>
  <!-- Details on Body -->
  <path d="M90,120 Q95,110 100,120" stroke="#000" stroke-width="1" fill="none"></path>
  <path d="M110,130 Q115,120 120,130" stroke="#000" stroke-width="1" fill="none"></path>
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
- Retain unicorn structure from base SVG.
- Add visual details based on the scene description.
- Include a viewBox="0 0 250 250".
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
- Include a viewBox="0 0 250 250".
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

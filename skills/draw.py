import os
import re
import time
from pathlib import Path
from PIL import Image
import cairosvg
import litellm
from openai import AsyncOpenAI
import asyncio

IMAGES_DIR = Path("static/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

async def generate_pippin_drawing(scene_description: str, api_key_openai: str, output_path: str = None) -> str:
    """
    Generate a whimsical drawing (JPEG) from a provided scene description.
    The process:
    - Extract the most visually interesting moment via GPT-4-like model
    - Request an SVG illustration via a smaller model (litellm)
    - Convert the SVG to PNG, then to JPEG
    - Return the path to the generated JPEG

    :param scene_description: A textual description of the scene to illustrate.
    :param api_key_openai: Your OpenAI API key.
    :param output_path: Optional path/filename for the final JPEG. If None, a timestamp-based name is used.
    :return: The path to the generated JPEG image.
    """
    if not api_key_openai:
        print("OpenAI API key not found. Cannot generate drawing.")
        return None

    client = AsyncOpenAI(api_key=api_key_openai)

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

    svg_prompt = f"""Create a whimsical, cute SVG illustration based on this scene:
    {scene_info}

    Requirements:
    - Keep the SVG simple and clean
    - Use solid colors instead of gradients
    - Include a viewBox attribute
    - Make it suitable for a children's book illustration
    - Ensure the SVG is well-formed and complete
    - Avoid using gradients, patterns, or filters
    - Use only basic SVG elements (path, rect, circle, etc.)

    Respond only with the SVG code.
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

import re
import time
import os
import cairosvg
from PIL import Image
from pathlib import Path
import asyncio
from openai import AsyncOpenAI
import litellm
from lxml import etree as ET

IMAGES_DIR = Path("static/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def is_float_str(s):
    return bool(re.match(r'^-?\d+(\.\d+)?$', s.strip()))

def is_hex_color(s):
    return bool(re.match(r'^#[0-9A-Fa-f]{6}$', s.strip()))

def hex_to_rgb(h):
    h = h.strip()
    return (int(h[1:3],16), int(h[3:5],16), int(h[5:7],16))

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def parse_numeric_list(s):
    parts = re.split(r'[\s,]+', s.strip())
    nums = []
    for p in parts:
        p = p.strip()
        if p and is_float_str(p):
            nums.append(float(p))
        else:
            return None
    return nums

def interpolate(a, b, t):
    return a + (b - a) * t

def interpolate_lists(list_a, list_b, t):
    return [interpolate(x, y, t) for x, y in zip(list_a, list_b)]

def interpolate_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0]-c1[0])*t),
        int(c1[1] + (c2[1]-c1[1])*t),
        int(c1[2] + (c2[2]-c1[2])*t)
    )

def parse_values_attribute(values_str):
    keyframes_str = values_str.split(';')
    keyframes = []
    numeric_mode = None
    color_mode = None

    for kf in keyframes_str:
        kf = kf.strip()
        nums = parse_numeric_list(kf)
        if nums is not None:
            if color_mode is True:
                return None
            numeric_mode = True
            keyframes.append(nums)
        else:
            if is_hex_color(kf):
                if numeric_mode is True:
                    return None
                color_mode = True
                rgb = hex_to_rgb(kf)
                keyframes.append(rgb)
            else:
                return None

    return keyframes

def get_keyframe_values(keyframes, t):
    n = len(keyframes) - 1
    if n <= 0:
        return keyframes[0] if keyframes else None

    segment_length = 1.0 / n
    segment_index = int(t // segment_length)
    if segment_index == n:
        return keyframes[-1]

    segment_t = (t - (segment_index * segment_length)) / segment_length
    start = keyframes[segment_index]
    end = keyframes[segment_index + 1]

    if isinstance(start, list) and isinstance(end, list):
        return interpolate_lists(start, end, segment_t)
    elif isinstance(start, tuple) and isinstance(end, tuple):
        return interpolate_color(start, end, segment_t)
    else:
        return None

def build_transform(transform_type, values):
    if transform_type == "translate":
        if len(values) == 1:
            return f"translate({values[0]},0)"
        elif len(values) >= 2:
            return f"translate({values[0]},{values[1]})"
    elif transform_type == "rotate":
        if len(values) == 1:
            return f"rotate({values[0]})"
        elif len(values) == 3:
            return f"rotate({values[0]} {values[1]} {values[2]})"
    elif transform_type == "scale":
        if len(values) == 1:
            return f"scale({values[0]})"
        elif len(values) == 2:
            return f"scale({values[0]} {values[1]})"
    elif transform_type == "skewX":
        if len(values) == 1:
            return f"skewX({values[0]})"
    elif transform_type == "skewY":
        if len(values) == 1:
            return f"skewY({values[0]})"
    return ""

async def generate_animated_unicorn(scene_description: str, api_key_openai: str, output_path: str = None) -> str:
    """
    Generate a whimsical animated unicorn GIF from a provided scene description.

    Steps:
    - Use a GPT model to determine scene details for a whimsical unicorn animation
    - Use a smaller model (litellm) to produce an animated SVG
    - Render multiple frames from the SVG's animations
    - Convert frames to a GIF
    - Return the path to the generated GIF
    """

    if not api_key_openai:
        print("OpenAI API key not found. Cannot generate animated unicorn.")
        return None

    client = AsyncOpenAI(api_key=api_key_openai)

    # Extract scene info
    system_msg = "You are an assistant that extracts details to create a whimsical animated unicorn scene."
    user_msg = f"""Given this memory, describe how to depict a unicorn in a whimsical, animated illustration:

Memory: {scene_description}

Format:
Scene: [describe the unicorn and surroundings]
Style: [children's book, whimsical]
Animated Elements: [which parts move and how, numeric or color attributes]
"""

    scene_response = await client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ]
    )
    scene_info = scene_response.choices[0].message.content.strip()

    # Base unicorn SVG (static)
    base_unicorn_svg = """
<svg width="1000" height="1000" viewBox="0 0 1000 1000" xmlns="http://www.w3.org/2000/svg">
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

    # Get animated SVG from litellm
    svg_prompt = f"""You have a base unicorn SVG (no animations):

{base_unicorn_svg}

Update this SVG to incorporate whimsical animations based on:
{scene_info}

Requirements:
- Retain unicorn structure from base SVG.
- Add multiple animations using <animate> or <animateTransform> with numeric or color values.
- For animateTransform, use numeric values.
- For color animations, use hex codes.
- Include a viewBox="0 0 1000 1000".
- No gradients or filters, just solid colors.
- Use a light colored background.
- Respond ONLY with the updated SVG code.
"""

    svg_response = litellm.completion(
        model="o1-mini",
        messages=[{"content": svg_prompt, "role": "user"}]
    )
    svg_text = svg_response['choices'][0]['message']['content']
    svg_pattern = re.compile(r'<svg[\s\S]*?<\/svg>', re.IGNORECASE)
    svg_match = svg_pattern.search(svg_text)
    if not svg_match:
        print("No valid animated SVG found in the response.")
        return None

    svg_code = svg_match.group(0)

    timestamp = int(time.time())
    if output_path is None:
        filename = f"unicorn_{timestamp}.gif"
        output_path = str(IMAGES_DIR / filename)
    else:
        output_path = str(IMAGES_DIR / output_path)

    # Parse SVG and collect animations
    root = ET.fromstring(svg_code)
    animations = []

    for anim in root.findall(".//{*}animate"):
        attr_name = anim.get("attributeName")
        from_val = anim.get("from")
        to_val = anim.get("to")
        dur = anim.get("dur")
        values = anim.get("values")
        if (from_val or to_val or values) and dur:
            parent_elem = anim.getparent()
            animations.append({
                'element': parent_elem,
                'attributeName': attr_name,
                'from': from_val,
                'to': to_val,
                'values': values,
                'dur': dur,
                'animate_element': anim,
                'type': 'animate'
            })

    for animtf in root.findall(".//{*}animateTransform"):
        attr_name = animtf.get("attributeName")
        from_val = animtf.get("from")
        to_val = animtf.get("to")
        values = animtf.get("values")
        dur = animtf.get("dur")
        transform_type = animtf.get("type")
        if (from_val or to_val or values) and dur and transform_type:
            parent_elem = animtf.getparent()
            animations.append({
                'element': parent_elem,
                'attributeName': attr_name,
                'from': from_val,
                'to': to_val,
                'values': values,
                'dur': dur,
                'transform_type': transform_type,
                'animate_element': animtf,
                'type': 'animateTransform'
            })

    for a in animations:
        if a['animate_element'] is not None:
            parent = a['animate_element'].getparent()
            if parent is not None:
                parent.remove(a['animate_element'])

    num_frames = 10
    frame_duration = 0.1
    frames_data = []

    for i in range(num_frames):
        t = i / (num_frames - 1) if num_frames > 1 else 0.0

        for anim in animations:
            duration = anim['dur']
            if duration.endswith('s'):
                dur_sec = float(duration[:-1])
            else:
                dur_sec = float(duration)
            anim_t = t  # normalized time from 0 to 1

            from_val = anim.get('from')
            to_val = anim.get('to')
            values = anim.get('values')

            if from_val and to_val:
                if is_hex_color(from_val) and is_hex_color(to_val):
                    c1 = hex_to_rgb(from_val)
                    c2 = hex_to_rgb(to_val)
                    c_cur = interpolate_color(c1, c2, anim_t)
                    anim['element'].set(anim['attributeName'], rgb_to_hex(c_cur))
                else:
                    f_list = parse_numeric_list(from_val)
                    t_list = parse_numeric_list(to_val)
                    if f_list and t_list:
                        cur_vals = interpolate_lists(f_list, t_list, anim_t)
                        if anim['type'] == 'animateTransform':
                            transform_type = anim.get('transform_type', '')
                            anim['element'].set('transform', build_transform(transform_type, cur_vals))
                        else:
                            if len(cur_vals) == 1:
                                anim['element'].set(anim['attributeName'], str(cur_vals[0]))
                            else:
                                anim['element'].set(anim['attributeName'], str(cur_vals[0]))
            elif values:
                keyframes = parse_values_attribute(values)
                if keyframes is None:
                    continue
                vals = get_keyframe_values(keyframes, anim_t)
                if vals is None:
                    continue
                if isinstance(vals, tuple) and len(vals) == 3:
                    # color
                    anim['element'].set(anim['attributeName'], rgb_to_hex(vals))
                elif isinstance(vals, list):
                    # numeric
                    if anim['type'] == 'animateTransform':
                        transform_type = anim.get('transform_type', '')
                        anim['element'].set('transform', build_transform(transform_type, vals))
                    else:
                        if len(vals) == 1:
                            anim['element'].set(anim['attributeName'], str(vals[0]))
                        else:
                            anim['element'].set(anim['attributeName'], str(vals[0]))

        frame_svg_code = ET.tostring(root, encoding='unicode')
        temp_svg = IMAGES_DIR / f"debug_unicorn_{time.time()}_frame_{i}.svg"
        with open(temp_svg, 'w') as f:
            f.write(frame_svg_code)

        temp_png = IMAGES_DIR / f"debug_unicorn_{time.time()}_frame_{i}.png"
        cairosvg.svg2png(url=str(temp_svg), write_to=str(temp_png))

        with Image.open(temp_png) as img:
            frames_data.append(img.convert("RGB"))

        temp_svg.unlink(missing_ok=True)
        temp_png.unlink(missing_ok=True)

    # Create GIF
    frames_data[0].save(
        output_path,
        save_all=True,
        append_images=frames_data[1:],
        duration=int(frame_duration * 1000),
        loop=0
    )

    return output_path

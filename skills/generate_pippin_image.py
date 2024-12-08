import os
import json
from PIL import Image, ImageDraw
from openai import OpenAI
from io import BytesIO
import requests
from pydantic import BaseModel
import math

class PippinPosition(BaseModel):
    x: float
    y: float
    size: float
    rotation: float

class SceneDescription(BaseModel):
    image_prompt: str
    pippin_position: PippinPosition

def quadratic_bezier_point(p0, p1, p2, t):
    """Calculate point on a quadratic Bézier curve at parameter t."""
    x = (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
    y = (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
    return (x, y)

def draw_quadratic_bezier(draw, p0, p1, p2, width=4, fill="black", steps=50):  # Increased default width
    """Draw a quadratic Bézier curve using many small line segments."""
    points = []
    for i in range(steps + 1):
        t = i / steps
        points.append(quadratic_bezier_point(p0, p1, p2, t))

    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=fill, width=width)
    return points

def create_pippin_image(size=(250, 250)):
    """Create Pippin unicorn using PIL with quadratic Bézier curves"""
    image = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Colors
    white = "#FFFFFF"
    black = "#000000"
    gold = "#FFD700"
    pink = "#FF69B4"

    # Scale factor
    scale_x = size[0] / 250
    scale_y = size[1] / 250

    def scale_point(x, y):
        return (x * scale_x, y * scale_y)

    # Body outline points
    body_segments = [
        [(80,150), (60,120), (80,90)],
        [(80,90), (100,60), (140,70)],
        [(140,70), (180,80), (160,120)],
        [(160,120), (150,160), (100,160)]
    ]

    # Draw body segments
    body_points = []
    for segment in body_segments:
        p0 = scale_point(*segment[0])
        p1 = scale_point(*segment[1])
        p2 = scale_point(*segment[2])
        points = draw_quadratic_bezier(draw, p0, p1, p2, width=4)  # Increased width
        body_points.extend(points)

    # Close the body path
    draw.line([body_points[-1], scale_point(80,150)], fill=black, width=4)  # Increased width

    # Fill body
    draw.polygon(body_points + [scale_point(80,150)], fill=white)

    # Head and neck
    head_segments = [
        [(140,70), (150,60), (160,55)],
        [(160,55), (170,50), (175,60)],
        [(175,60), (180,70), (170,80)],
        [(170,80), (160,85), (150,80)],
        [(150,80), (140,75), (140,70)]
    ]

    # Draw head segments
    head_points = []
    for segment in head_segments:
        p0 = scale_point(*segment[0])
        p1 = scale_point(*segment[1])
        p2 = scale_point(*segment[2])
        points = draw_quadratic_bezier(draw, p0, p1, p2, width=4)  # Increased width
        head_points.extend(points)

    # Fill head
    draw.polygon(head_points, fill=white)

    # Horn
    horn_points = [
        scale_point(160,55),
        scale_point(155,35),
        scale_point(165,35)
    ]
    draw.polygon(horn_points, fill=gold, outline=black)

    # Eyes
    eye_center = scale_point(162, 60)
    eye_radius = int(3 * scale_x)
    draw.ellipse((
        eye_center[0] - eye_radius,
        eye_center[1] - eye_radius,
        eye_center[0] + eye_radius,
        eye_center[1] + eye_radius
    ), fill=black)

    # Eye highlight
    highlight_center = scale_point(158, 60)
    highlight_radius = int(1.5 * scale_x)
    draw.ellipse((
        highlight_center[0] - highlight_radius,
        highlight_center[1] - highlight_radius,
        highlight_center[0] + highlight_radius,
        highlight_center[1] + highlight_radius
    ), fill=white)

    # Mane
    mane_segments = [
        [(155,55), (150,60), (155,65)],
        [(155,65), (150,70), (155,75)],
        [(155,75), (150,80), (155,85)],
        [(160,55), (155,60), (160,65)],
        [(160,65), (155,70), (160,75)],
        [(160,75), (155,80), (160,85)]
    ]

    for segment in mane_segments:
        p0 = scale_point(*segment[0])
        p1 = scale_point(*segment[1])
        p2 = scale_point(*segment[2])
        draw_quadratic_bezier(draw, p0, p1, p2, width=4, fill=pink)  # Increased width

    # Back legs (straight lines)
    for x in [100, 120, 140]:
        start = scale_point(x, 160)
        end = scale_point(x, 190)
        draw.line([start, end], fill=black, width=4)  # Increased width

        # Hooves
        hoof_center = scale_point(x, 190)
        draw.ellipse((
            hoof_center[0] - 5 * scale_x,
            hoof_center[1] - 2 * scale_y,
            hoof_center[0] + 5 * scale_x,
            hoof_center[1] + 2 * scale_y
        ), fill=black)

    # Front leg with curve (from the SVG path)
    front_leg_points = [(160,120), (165,140), (160,160)]
    p0 = scale_point(*front_leg_points[0])
    p1 = scale_point(*front_leg_points[1])
    p2 = scale_point(*front_leg_points[2])
    draw_quadratic_bezier(draw, p0, p1, p2, width=4)  # Increased width

    # Front hoof
    front_hoof_center = scale_point(160, 160)
    draw.ellipse((
        front_hoof_center[0] - 5 * scale_x,
        front_hoof_center[1] - 2 * scale_y,
        front_hoof_center[0] + 5 * scale_x,
        front_hoof_center[1] + 2 * scale_y
    ), fill=black)

    # Tail
    tail_segments = [
        [(80,150), (70,155), (75,160)],
        [(75,160), (70,165), (80,170)],
        [(75,160), (80,165), (75,170)]
    ]

    for segment in tail_segments:
        p0 = scale_point(*segment[0])
        p1 = scale_point(*segment[1])
        p2 = scale_point(*segment[2])
        draw_quadratic_bezier(draw, p0, p1, p2, width=4, fill=pink)  # Increased width

    return image

def generate_pippin_image(description: str, api_key: str, output_path: str = "pippin_scene.png"):
    """
    Generates an image with Pippin the unicorn placed in a scene based on the description.
    """
    print("Starting image generation process...")

    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=api_key)
        print("OpenAI client initialized successfully")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        raise

    try:
        print("Requesting scene description from GPT-4...")
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """
                Generate a detailed image description and positioning data for a unicorn named Pippin.
                Provide the background scene description and Pippin's position in the scene. Since pippin will be added after, do not include Pippin or any mention of unicorns in the background description (unless we're depicting a second unicorn, etc).
                For position, x and y should be between 0 and 1 (as percentage from left/top),
                size should be between 0 and 1 (as relative size),
                and rotation should be in degrees (0-360).
                """},
                {"role": "user", "content": description}
            ],
            response_format=SceneDescription
        )

        scene_data = completion.choices[0].message.parsed
        print(f"Parsed scene data: {json.dumps(scene_data.model_dump(), indent=2)}")

    except Exception as e:
        print(f"Error in GPT-4 processing: {e}")
        raise

    try:
        # Generate the background image using DALL-E
        print("Requesting image generation from DALL-E...")
        image_response = client.images.generate(
            model="dall-e-3",
            prompt=scene_data.image_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        print("Successfully received DALL-E response")

        # Download the generated image
        background_image_url = image_response.data[0].url
        print(f"Downloading background image from URL: {background_image_url}")
        background_image_response = requests.get(background_image_url)
        background_image = Image.open(BytesIO(background_image_response.content))
        print("Successfully downloaded and opened background image")

    except Exception as e:
        print(f"Error in DALL-E image generation/download: {e}")
        raise

    try:
        print("Creating Pippin image...")
        # Create Pippin at larger size for better quality
        pippin_image = create_pippin_image((500, 500))
        print("Successfully created Pippin image")

        # Calculate Pippin's size and position
        bg_width, bg_height = background_image.size
        position = scene_data.pippin_position
        print(f"Background image size: {bg_width}x{bg_height}")
        print(f"Pippin original size: {pippin_image.size}")

        # Calculate new size for Pippin
        desired_width = int(bg_width * position.size)
        ratio = desired_width / pippin_image.size[0]
        new_size = (desired_width, int(pippin_image.size[1] * ratio))
        print(f"Calculated new size for Pippin: {new_size}")

        # Resize Pippin
        pippin_image = pippin_image.resize(new_size, Image.Resampling.LANCZOS)
        print("Successfully resized Pippin")

        # Rotate Pippin
        print(f"Rotating Pippin by {position.rotation} degrees...")
        pippin_image = pippin_image.rotate(-position.rotation, expand=True, resample=Image.Resampling.BICUBIC)
        print("Successfully rotated Pippin")

        # Calculate final position
        x_pos = int(position.x * bg_width - pippin_image.size[0] / 2)
        y_pos = int(position.y * bg_height - pippin_image.size[1] / 2)
        print(f"Final position calculated - x: {x_pos}, y: {y_pos}")

        # Create a new image with transparency
        final_image = background_image.copy()

        # Paste Pippin onto the background
        print("Pasting Pippin onto background...")
        final_image.paste(pippin_image, (x_pos, y_pos), pippin_image)

        # Save the final image
        print(f"Saving final image to: {output_path}")
        final_image.save(output_path)
        print("Image saved successfully")

    except Exception as e:
        print(f"Error during image processing: {e}")
        raise

    return output_path

# Example usage
if __name__ == "__main__":
    try:
        print("Starting script execution...")
        api_key = os.environ['OPENAI_API_KEY']
        description = "Pippin in the royal court of King Henry VIII"
        output = generate_pippin_image(description, api_key)
        print(f"Script completed successfully. Output saved to: {output}")
    except Exception as e:
        print(f"Script failed with error: {e}")
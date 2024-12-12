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

    # Scale factor - now using larger base coordinates
    scale_x = size[0] / 250
    scale_y = size[1] / 250

    def scale_point(x, y):
        return (x * scale_x, y * scale_y)

    # Body outline points - scaled up by ~1.5x
    body_segments = [
        [(120, 180), (90, 140), (120, 100)],
        [(120, 100), (150, 60), (190, 75)],
        [(190, 75), (240, 90), (210, 140)],
        [(210, 140), (200, 190), (150, 190)]
    ]

    # Draw body segments
    body_points = []
    for segment in body_segments:
        p0 = scale_point(*segment[0])
        p1 = scale_point(*segment[1])
        p2 = scale_point(*segment[2])
        points = draw_quadratic_bezier(draw, p0, p1, p2, width=6)  # Increased width
        body_points.extend(points)

    # Close the body path
    draw.line([body_points[-1], scale_point(120, 180)], fill=black, width=6)

    # Fill body
    draw.polygon(body_points + [scale_point(120, 180)], fill=white)

    # Head and neck - scaled up
    head_segments = [
        [(190, 75), (205, 65), (220, 58)],
        [(220, 58), (235, 50), (242, 65)],
        [(242, 65), (250, 80), (235, 95)],
        [(235, 95), (220, 102), (205, 95)],
        [(205, 95), (190, 88), (190, 75)]
    ]

    # Draw head segments
    head_points = []
    for segment in head_segments:
        p0 = scale_point(*segment[0])
        p1 = scale_point(*segment[1])
        p2 = scale_point(*segment[2])
        points = draw_quadratic_bezier(draw, p0, p1, p2, width=6)
        head_points.extend(points)

    # Fill head
    draw.polygon(head_points, fill=white)

    # Horn - made slightly larger
    horn_points = [
        scale_point(220, 58),
        scale_point(213, 30),
        scale_point(227, 30)
    ]
    draw.polygon(horn_points, fill=gold, outline=black)

    # Eyes - scaled up
    eye_center = scale_point(223, 65)
    eye_radius = int(4.5 * scale_x)  # Increased size
    draw.ellipse((
        eye_center[0] - eye_radius,
        eye_center[1] - eye_radius,
        eye_center[0] + eye_radius,
        eye_center[1] + eye_radius
    ), fill=black)

    # Eye highlight
    highlight_center = scale_point(217, 65)
    highlight_radius = int(2.5 * scale_x)  # Increased size
    draw.ellipse((
        highlight_center[0] - highlight_radius,
        highlight_center[1] - highlight_radius,
        highlight_center[0] + highlight_radius,
        highlight_center[1] + highlight_radius
    ), fill=white)

    # Mane - scaled up
    mane_segments = [
        [(215, 58), (208, 65), (215, 72)],
        [(215, 72), (208, 80), (215, 88)],
        [(215, 88), (208, 95), (215, 102)],
        [(222, 58), (215, 65), (222, 72)],
        [(222, 72), (215, 80), (222, 88)],
        [(222, 88), (215, 95), (222, 102)]
    ]

    for segment in mane_segments:
        p0 = scale_point(*segment[0])
        p1 = scale_point(*segment[1])
        p2 = scale_point(*segment[2])
        draw_quadratic_bezier(draw, p0, p1, p2, width=6, fill=pink)

    # Back legs (straight lines) - scaled up
    for x in [150, 175, 200]:
        start = scale_point(x, 190)
        end = scale_point(x, 230)
        draw.line([start, end], fill=black, width=6)

        # Hooves - made larger
        hoof_center = scale_point(x, 230)
        draw.ellipse((
            hoof_center[0] - 8 * scale_x,
            hoof_center[1] - 3 * scale_y,
            hoof_center[0] + 8 * scale_x,
            hoof_center[1] + 3 * scale_y
        ), fill=black)

    # Front leg with curve - scaled up
    front_leg_points = [(210, 140), (217, 165), (210, 190)]
    p0 = scale_point(*front_leg_points[0])
    p1 = scale_point(*front_leg_points[1])
    p2 = scale_point(*front_leg_points[2])
    draw_quadratic_bezier(draw, p0, p1, p2, width=6)

    # Front hoof - made larger
    front_hoof_center = scale_point(210, 190)
    draw.ellipse((
        front_hoof_center[0] - 8 * scale_x,
        front_hoof_center[1] - 3 * scale_y,
        front_hoof_center[0] + 8 * scale_x,
        front_hoof_center[1] + 3 * scale_y
    ), fill=black)

    # Tail - scaled up
    tail_segments = [
        [(120, 180), (105, 187), (112, 194)],
        [(112, 194), (105, 202), (120, 210)],
        [(112, 194), (120, 202), (112, 210)]
    ]

    for segment in tail_segments:
        p0 = scale_point(*segment[0])
        p1 = scale_point(*segment[1])
        p2 = scale_point(*segment[2])
        draw_quadratic_bezier(draw, p0, p1, p2, width=6, fill=pink)

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
        import random

        # List of art styles to randomly suggest
        art_styles = [
            "rubber hose", "watercolor", "line art with soft shading", 
            "chibi", "fantasy", "cartoon", "art nouveau", 
            "digital with glow effects", "impressionist", 
            "steampunk", "pixel art", "sketch", 
            "oil painting", "low-poly", "minimalist",
            "cubism", "vaporwave", "surrealism", 
            "graffiti", "pop art", "anime", 
            "hyperrealism", "cyberpunk", "gothic", 
            "baroque", "sci-fi concept art", "charcoal drawing", 
            "mosaic", "flat design", "mid-century modern", 
            "collage", "isometric", "doodle"
        ]

        # Select a random art style
        random_style = random.choice(art_styles)

        print("Requesting scene description from GPT-4...")
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""
                Generate a detailed image description and positioning data for a unicorn named Pippin.
                Provide the background scene description and Pippin's position in the scene. 
                Since Pippin will be added after, do not include Pippin or any mention of unicorns in the background description (unless we're depicting a second unicorn, etc).
                For position, x and y should be between 0 and 1 (as percentage from left/top),
                size should be between 0 and 1 (as relative size),
                and rotation should be in degrees (0-360).
                Specify the suggested art style provided below in the image description.

                Suggested art style: {random_style}.
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
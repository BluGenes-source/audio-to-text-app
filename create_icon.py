from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # Create a 256x256 image with transparent background
    size = 256
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Define colors
    primary_color = "#2962ff"  # Material Blue (matching our app theme)
    secondary_color = "#768fff"
    
    # Draw a rounded rectangle for audio waveform background
    padding = 40
    draw.rounded_rectangle(
        [padding, padding, size-padding, size-padding],
        radius=20,
        fill=primary_color
    )
    
    # Draw simplified waveform representation
    wave_height = 80
    wave_width = size - (padding * 3)
    wave_y = size // 2
    wave_points = []
    
    # Create a simple waveform pattern
    for x in range(padding * 2, padding * 2 + wave_width, 20):
        y1 = wave_y - wave_height//2
        y2 = wave_y + wave_height//2
        draw.rectangle([x, y1, x+8, y2], fill=secondary_color)
    
    # Add text overlay "T" for Text
    overlay_color = "#FFFFFF"
    font_size = 120
    try:
        # Try to use Arial, fallback to default if not available
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    text = "T"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Position text in center
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    draw.text((x, y), text, fill=overlay_color, font=font)
    
    # Save in multiple sizes for Windows icon
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []
    
    for size in icon_sizes:
        resized_image = image.resize(size, Image.Resampling.LANCZOS)
        images.append(resized_image)
    
    # Save as ICO file
    icon_path = os.path.join(os.path.dirname(__file__), 'app.ico')
    image.save(icon_path, format='ICO', sizes=icon_sizes)
    print(f"Icon created successfully at: {icon_path}")

if __name__ == "__main__":
    create_icon()
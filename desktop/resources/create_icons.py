#!/usr/bin/env python3
"""
Create default icon resources for the desktop application.

This script generates simple placeholder icons for the system tray.
In a production environment, these would be replaced with professionally
designed icons.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def create_icon(filename: str, size: int = 64, color: str = 'white',
                text: str = 'GA', text_color: str = 'black') -> None:
    """
    Create a simple icon with text.

    Args:
        filename: Output filename (e.g., 'icon.png')
        size: Icon size in pixels (default: 64x64)
        color: Background color (default: 'white')
        text: Text to display on icon (default: 'GA')
        text_color: Text color (default: 'black')
    """
    # Create image with colored background
    img = Image.new('RGB', (size, size), color=color)
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default if unavailable
    try:
        # Try to use a system font (size should be appropriate for icon)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size // 3)
    except (OSError, IOError):
        # Fall back to default font
        font = ImageFont.load_default()

    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Calculate centered position
    x = (size - text_width) // 2 - bbox[0]
    y = (size - text_height) // 2 - bbox[1]

    # Draw text
    draw.text((x, y), text, fill=text_color, font=font)

    # Save icon
    output_path = Path(__file__).parent / filename
    img.save(output_path, 'PNG')
    print(f"Created: {output_path}")


def main():
    """Create all required icons."""
    print("Creating desktop application icons...")
    print("-" * 60)

    # icon.png - Main icon (white background with black "GA" text)
    create_icon('icon.png', size=64, color='white', text='GA', text_color='black')

    # icon_gray.png - Inactive state (gray background with dark gray text)
    create_icon('icon_gray.png', size=64, color='lightgray', text='GA', text_color='darkgray')

    # icon_active.png - Active state (blue background with white text)
    create_icon('icon_active.png', size=64, color='royalblue', text='GA', text_color='white')

    print("-" * 60)
    print("✓ All icons created successfully!")
    print("\nNote: These are placeholder icons. For production use,")
    print("replace with professionally designed icons.")


if __name__ == '__main__':
    main()

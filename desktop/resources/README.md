# Desktop Application Icons

This directory contains icon resources for the Grading App desktop application's system tray.

## Available Icons

| File | Size | Purpose | Description |
|------|------|---------|-------------|
| `icon.png` | 64x64 | Main icon | White background with black "GA" text |
| `icon_gray.png` | 64x64 | Inactive state | Light gray background with dark gray "GA" text |
| `icon_active.png` | 64x64 | Active state | Royal blue background with white "GA" text |

## Creating Icons

### Quick Start

Run the icon creation script to generate all required icons:

```bash
cd desktop/resources
python create_icons.py
```

This will create three placeholder icons with the "GA" text logo.

### Custom Icons

For production use, replace the placeholder icons with professionally designed versions:

1. **Design Requirements**:
   - Format: PNG with transparency
   - Size: 64x64 pixels (minimum), 128x128 recommended
   - Color depth: 32-bit RGBA
   - Content: Simple, recognizable design

2. **Platform Considerations**:
   - **Windows**: Icons work best at 16x16, 32x32, 48x48
   - **macOS**: Menu bar icons should be monochrome (system renders them)
   - **Linux**: Full color icons recommended

3. **Replace Files**:
   ```bash
   # Backup originals
   cp icon.png icon.png.bak

   # Copy your custom icons
   cp /path/to/your/icon.png icon.png
   cp /path/to/your/icon_gray.png icon_gray.png
   cp /path/to/your/icon_active.png icon_active.png
   ```

## Icon States

### Main Icon (`icon.png`)
- **Usage**: Default system tray icon
- **When**: App is running normally
- **Design**: Should be recognizable and on-brand

### Inactive Icon (`icon_gray.png`)
- **Usage**: When app is in background/idle state
- **When**: No active tasks running (future use)
- **Design**: Grayed-out version of main icon

### Active Icon (`icon_active.png`)
- **Usage**: When app is processing/active
- **When**: Tasks running, updates downloading (future use)
- **Design**: Highlighted/colorful version of main icon

## Technical Details

### Image Format

```python
from PIL import Image

# Load icon
icon = Image.open('icon.png')

# Verify format
assert icon.format == 'PNG'
assert icon.size == (64, 64)
assert icon.mode == 'RGB' or icon.mode == 'RGBA'
```

### Fallback Behavior

If icon files are missing, the application creates a default white square:

```python
from PIL import Image

# Default icon (automatic fallback)
default_icon = Image.new('RGB', (64, 64), color='white')
```

### Platform-Specific Rendering

#### Windows
```python
# Windows renders icons at multiple sizes
# Best to provide: 16x16, 32x32, 48x48, 64x64
icon_sizes = [16, 32, 48, 64]
```

#### macOS
```python
# macOS menu bar icons are typically monochrome
# System applies tint based on light/dark mode
# Recommend: Simple, high-contrast design
```

#### Linux
```python
# Linux supports full color icons
# Different desktop environments have different sizes
# GNOME: 24x24, KDE: 22x22, XFCE: 16x16
```

## Icon Design Guidelines

### Do's ✅

- Keep design simple and recognizable
- Use high contrast for visibility
- Test on light and dark backgrounds
- Ensure icon works at small sizes (16x16)
- Use consistent style across all states

### Don'ts ❌

- Don't use too much detail (won't scale well)
- Don't use very thin lines (hard to see)
- Don't use gradients (may not render well)
- Don't use text smaller than 8pt
- Don't use too many colors (keep it simple)

## Icon Creation Script

The `create_icons.py` script generates simple placeholder icons using PIL:

```python
from PIL import Image, ImageDraw, ImageFont

def create_icon(filename, size=64, color='white', text='GA', text_color='black'):
    """Create a simple icon with text."""
    img = Image.new('RGB', (size, size), color=color)
    draw = ImageDraw.Draw(img)

    # Try to use system font, fallback to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size // 3)
    except:
        font = ImageFont.load_default()

    # Center text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2 - bbox[0]
    y = (size - text_height) // 2 - bbox[1]

    # Draw text
    draw.text((x, y), text, fill=text_color, font=font)

    # Save
    img.save(filename, 'PNG')
```

### Customizing the Script

Edit `create_icons.py` to customize the generated icons:

```python
# Change icon size
create_icon('icon.png', size=128, ...)

# Change colors
create_icon('icon.png', color='#4A90E2', text_color='white', ...)

# Change text
create_icon('icon.png', text='APP', ...)

# Add border
def create_icon_with_border(filename, ...):
    img = create_icon(...)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (size-1, size-1)], outline='black', width=2)
    img.save(filename)
```

## Tools for Icon Design

### Recommended Software

- **Adobe Illustrator**: Professional vector graphics
- **Inkscape**: Free vector graphics editor
- **GIMP**: Free raster graphics editor
- **Figma**: Web-based design tool
- **Affinity Designer**: Affordable vector graphics

### Online Tools

- **Flaticon**: Free icon library
- **Icons8**: Icon generator and library
- **Canva**: Simple icon design
- **Pixlr**: Online photo editor

### Icon Optimization

```bash
# Optimize PNG files
pngquant icon.png --output icon-optimized.png
optipng -o7 icon.png

# Convert SVG to PNG (multiple sizes)
for size in 16 32 48 64 128; do
    inkscape -w $size -h $size icon.svg -o icon-${size}.png
done
```

## Testing Icons

### Visual Test

```python
from PIL import Image

# Load and display icon
icon = Image.open('icon.png')
icon.show()

# Check size and format
print(f"Size: {icon.size}")
print(f"Format: {icon.format}")
print(f"Mode: {icon.mode}")
```

### System Tray Test

```python
import pystray
from PIL import Image

# Test icon in system tray
image = Image.open('icon.png')
icon = pystray.Icon('Test', image, 'Test Icon')

# Run (Ctrl+C to stop)
icon.run()
```

### All Platforms Test

Test icons on all target platforms:

1. **Windows**: Right-click system tray to see icon
2. **macOS**: Check menu bar (top-right)
3. **Linux**: Check system tray (varies by DE)

## Troubleshooting

### Icon Not Showing

**Problem**: Icon appears as blank/generic

**Solutions**:
- Verify PNG format: `file icon.png`
- Check file permissions: `chmod 644 icon.png`
- Ensure non-zero size: `ls -lh icon.png`
- Test with PIL: `python -c "from PIL import Image; Image.open('icon.png').show()"`

### Icon Too Pixelated

**Problem**: Icon looks blurry or pixelated

**Solutions**:
- Increase icon size to 128x128 or higher
- Use vector graphics (SVG) as source
- Export at 2x resolution for retina displays
- Use anti-aliasing in design software

### Wrong Colors

**Problem**: Icon colors don't match design

**Solutions**:
- Check color mode: `RGB` not `CMYK`
- Verify color profile (sRGB recommended)
- Test on different backgrounds
- Check alpha transparency

## Future Improvements

- [ ] SVG source files for scalability
- [ ] Icon set for different sizes (16, 32, 48, 64, 128, 256)
- [ ] Platform-specific icons (Windows .ico, macOS .icns)
- [ ] Animated icons for active state
- [ ] Dark mode variants
- [ ] Retina display support (2x, 3x)

## License

These placeholder icons are provided for development use. Replace with properly licensed icons for production.

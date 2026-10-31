"""Regenerate icon.png / icon.ico from app_icon_source.jpg. Run from the project root."""
from PIL import Image, ImageDraw

img = Image.open('app_icon_source.jpg').convert("RGBA")
width, height = img.size

# Get background color from top-left pixel
bg_color = img.getpixel((0, 0))

# Create a square image with the background color
square_size = max(width, height)
square_img = Image.new('RGBA', (square_size, square_size), bg_color)

# Paste the original image into the center of the square
paste_x = (square_size - width) // 2
paste_y = (square_size - height) // 2
square_img.paste(img, (paste_x, paste_y))

# Function to add rounded corners


def add_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2 - 1, rad * 2 - 1), fill=255)
    alpha = Image.new('L', im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im


# Apple macOS squircle radius is roughly 22.5% of the size
radius = int(square_size * 0.225)
rounded_img = add_corners(square_img, radius)

rounded_img.save('icon.png')
# Save as ICO (requires no alpha for background? No, ICO supports alpha)
rounded_img.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32)])

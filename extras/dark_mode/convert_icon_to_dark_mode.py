# Helper script to Convert icon.png to icon.dark.png for Revit Dark theme

from PIL import Image # pip install pillow
import os

def create_dark_icon(source):
    """
    Creates a dark mode icon from the given source image.

    Args:
        source (str): The path to the source image file.

    Returns:
        None
    """
    image = Image.open(source).convert('RGBA')
    create_bitmap(image, (235, 235, 235), os.path.join(os.path.dirname(source), os.path.splitext(source)[0] + ".dark.png"))

def create_bitmap(source, color, target):
    """
    Creates a bitmap image with the given color and saves it to the target file.

    Args:
        source (PIL.Image): The source image to convert.
        color (tuple): The RGB or RGBA color tuple to use for the bitmap.
        target (str): The path to the target file.

    Returns:
        None
    """
    output = Image.new(source.mode, source.size)
    for x in range(source.width):
        for y in range(source.height):
            pixel = source.getpixel((x, y))
            if len(pixel) < 4 or pixel[3] == 0:
                output.putpixel((x, y), pixel)
            else:
                output.putpixel((x, y), (color[0], color[1], color[2], pixel[3]))
    output.save(target)

if __name__ == "__main__":
    # all icon.png files in the current directory and subfolders
    for root, dirs, files in os.walk("C:\pyRevit"):         # folder path that requires conversion
        for file in files:
            if file == "icon.png" and not os.path.exists(os.path.join(root, "icon.dark.png")):
                try:
                    create_dark_icon(os.path.join(root, file))
                except Exception as e:
                    print(e, "for  ", os.path.join(root, file))

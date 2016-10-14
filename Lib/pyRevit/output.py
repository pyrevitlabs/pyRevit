from .config import OUTPUT_WINDOW

def set_width(width):
    OUTPUT_WINDOW.Width = width

def close():
    OUTPUT_WINDOW.Close()

def hide():
    OUTPUT_WINDOW.Hide()

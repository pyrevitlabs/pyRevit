from .config import OUTPUT_WINDOW

# todo turn this into a class
def set_width(width):
    OUTPUT_WINDOW.Width = width


def close():
    OUTPUT_WINDOW.Close()


def hide():
    OUTPUT_WINDOW.Hide()

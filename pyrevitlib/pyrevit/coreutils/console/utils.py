import random

def random_hex_color():
    r = lambda: random.randint(0,255)
    return '#%02X%02X%02X' % (r(), r(), r())


def random_rgb_color():
    r = lambda: random.randint(0,255)
    return 'rgb(%d, %d, %d)' % (r(), r(), r())


def random_rgba_color():
    r = lambda: random.randint(0,255)
    a = lambda: round(random.random(), 2)
    return 'rgba(%d, %d, %d, %.2f)' % (r(), r(), r(), a())

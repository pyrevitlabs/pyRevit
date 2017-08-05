import random


def random_color():
    return random.randint(0, 255)


def random_alpha():
    return round(random.random(), 2)


def random_hex_color():
    return '#%02X%02X%02X' % (random_color(),
                              random_color(),
                              random_color())


def random_rgb_color():
    return 'rgb(%d, %d, %d)' % (random_color(),
                                random_color(),
                                random_color())


def random_rgba_color():
    return 'rgba(%d, %d, %d, %.2f)' % (random_color(),
                                       random_color(),
                                       random_color(),
                                       random_alpha())

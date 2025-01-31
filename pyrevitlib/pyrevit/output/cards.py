# -*- coding: UTF-8 -*-

""" This module contains functions to generate HTML cards for use in pyRevit output. """


def card_start_style(limit, value, alt):
    """
    Generates an HTML div element with a specific background color based on the ratio of value to limit.

    Args:
        limit (float): The limit value used to calculate the ratio.
        value (float): The current value to be compared against the limit.
        alt (str): The alt text for the div element.

    Returns:
        str: An HTML div element as a string with inline styles and the specified background color.
    The background color is determined by the following rules:
        - 'Grey' if value is 0 or if an exception occurs during ratio calculation.
        - 'Green' if 0 <= ratio < 0.5.
        - 'Orange' if 0.5 <= ratio <= 1.
        - 'Red' if ratio > 1.
    """
    try:
        ratio = float(value) / float(limit)
    except ZeroDivisionError:
        ratio = 0
    color = "#d0d3d4"
    if value != 0:
        if ratio < 0.5:
            color = "#D0E6A5"  # green
        elif ratio <= 1:
            color = "#FFDD94"  # orange
        else:
            color = "#FA897B"  # red
    try:
        card_start = '<div style="display: inline-block; width: 100px; height: 40px; background: {}; font-family: sans-serif; font-size: 0.85rem; padding: 5px; text-align: center; border-radius: 8px; margin: 5px; box-shadow: 0 6px 6px 0 rgba(0, 0, 0, 0.2); vertical-align: top;" alt="{}">'.format(
            color, alt
        )
    except Exception as e:
        print(e)
    return card_start


def card_builder(limit, value, description):
    """
    Builds an HTML card with the given limit, value, and description.

    Args:
        limit (int): The limit value to be displayed in the card.
        value (int or str): The main value to be displayed in the card.
        description (str): A description to be displayed in the card.

    Returns:
        str: A string containing the HTML representation of the card.
    """

    alt = "{} {} (limit = {})".format(str(value), str(description), str(limit))
    card_end = '<b>{}</b><br /><a style="font-size: 0.70rem">{}</a></div>'.format(
        value, description
    )
    return card_start_style(limit, value, alt) + card_end


def create_frame(title, *cards):
    """
    Creates an HTML div frame containing multiple cards with a rounded border and a title on the top left corner.

    return card_start_style(limit, value, alt) + card_end
        cards (str): Multiple strings representing HTML card elements.

    Returns:
        str: A string containing the HTML representation of the div frame.

    """
    # Add vertical-align: top to the frame and adjust title position
    frame_start = '<div style="display: inline-block; vertical-align: top; border: 1px solid #ccc; border-radius: 10px; padding: 5px; margin: 10px 5px 10px 5px; position: relative;">'
    title_html = '<div style="position: absolute; top: -12px; left: 10px; background: white; padding: 0 5px; font-weight: bold;">{}</div>'.format(
        title
    )
    cards_html = "".join(cards)
    frame_end = "</div>"
    return frame_start + title_html + cards_html + frame_end

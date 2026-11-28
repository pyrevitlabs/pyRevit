# -*- coding: utf-8 -*-
"""Pick only model elements by drawing a rectangle."""

import selectionpick


def is_model_element(element):
    return not element.ViewSpecific


if __name__ == "__main__":
    selectionpick.select_picked(is_model_element)

# -*- coding: utf-8 -*-
"""Discard pinned elements from the selection, or from a picked rectangle."""

import selectionpick


def is_not_pinned(element):
    return not element.Pinned


if __name__ == "__main__":
    selectionpick.keep_matching(is_not_pinned)

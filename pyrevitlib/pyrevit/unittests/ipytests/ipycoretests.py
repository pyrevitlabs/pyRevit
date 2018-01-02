# -*- coding: utf-8 -*-
from unittest import TestCase
from pyrevit.compat import safe_strtype


class TestCIronPythonEngine(TestCase):
    def test_unicode(self):
        """Convert unicode test"""
        ustr1 = '中國哲學書電子化計劃'
        ustr2 = 'A200•'
        temp = safe_strtype(ustr1)
        temp = safe_strtype(ustr2)

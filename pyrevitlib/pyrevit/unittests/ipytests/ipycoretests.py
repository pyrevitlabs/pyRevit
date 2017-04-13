# -*- coding: utf-8 -*-
from unittest import TestCase


class TestCIronPythonEngine(TestCase):
    def test_unicode(self):
        """Convert unicode test"""
        ustr1 = '中國哲學書電子化計劃'
        ustr2 = 'A200•'
        temp = str(ustr1)
        temp = str(ustr2)

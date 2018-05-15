"""Interoperability with other applications."""

import sys
import os

binary_path = os.path.join(os.path.dirname(__file__), 'bin')
sys.path.append(binary_path)

# pylama:ignore=E402,W0611
import clr
clr.AddReference('System')

import System

import winterops.bbx
import winterops.dxf
import winterops.ifc
import winterops.pts
import winterops.rhino
import winterops.stl
import winterops.xl
import winterops.yaml


__version__ = '0.2'

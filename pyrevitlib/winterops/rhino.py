# pylama:ignore=E402,W0611
from winterops import clr, System

clr.AddReference('System.Core')
clr.ImportExtensions(System.Linq)
clr.AddReferenceByName('Rhino3dmIO')

import Rhino

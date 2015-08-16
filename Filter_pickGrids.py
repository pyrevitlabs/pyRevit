import sys, os
sys.path.append( os.path.dirname( __file__ ))
import pyRevit as pr

__window__.Close()

pr.pickByCategory( "Grid" )
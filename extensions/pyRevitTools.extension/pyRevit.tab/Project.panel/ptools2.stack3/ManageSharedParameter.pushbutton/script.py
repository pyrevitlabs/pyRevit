# coding: utf8

__doc__ = """Interface to manage shared parameters
Features : create, modify, duplicate, save to definition file, delete multiple parameters, 
open multiple parameter groups in the same datagrid, create a new definition file, create from csv, 
return selected parameter for another use (e.g. create project parameters, family parameters)"""
__title__ = "SharedParameters"
__author__ = "Cyril Waechter"

from pypevitmep.parameter.manageshared import ManageSharedParameter

ManageSharedParameter.show_dialog()


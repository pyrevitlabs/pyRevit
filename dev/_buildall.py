"""Build all"""
from typing import Dict

import _autocomplete as autocomp
import _build as build


def build_all(_: Dict[str, str]):
    """Build all projects under pyRevit dev"""
    build.build_labs(_)
    build.build_engines(_)
    build.build_telemetry(_)
    autocomp.build_autocomplete(_)

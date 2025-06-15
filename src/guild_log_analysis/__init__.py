"""
Guild Log Analysis Package.

A comprehensive tool for analyzing World of Warcraft guild logs from
Warcraft Logs API.
"""

__version__ = "1.0.0"
__author__ = "Jonathan Sasse"
__email__ = "jonathan.sasse@outlook.de"

from .analysis.base import BossAnalysisBase
from .analysis.bosses.one_armed_bandit import OneArmedBanditAnalysis
from .api.client import WarcraftLogsAPIClient

__all__ = [
    "BossAnalysisBase",
    "OneArmedBanditAnalysis",
    "WarcraftLogsAPIClient",
]

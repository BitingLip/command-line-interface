"""
BitingLip CLI Package

Unified command-line interface for the BitingLip AI inference platform.
Provides access to all platform services through the gateway manager.
"""

__version__ = "1.0.0"
__author__ = "BitingLip Team"

from .config import CLIConfig, OutputFormat
from .client import BitingLipClient

__all__ = ["CLIConfig", "OutputFormat", "BitingLipClient"]

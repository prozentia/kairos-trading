"""Technical indicators package.

Public API:
    BaseIndicator   - abstract base class for indicators
    register        - decorator to register an indicator
    get_registry    - access the global IndicatorRegistry singleton
"""

from core.indicators.base import BaseIndicator
from core.indicators.registry import IndicatorRegistry, register, get_registry

__all__ = ["BaseIndicator", "IndicatorRegistry", "register", "get_registry"]

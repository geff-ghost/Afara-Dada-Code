"""
Finding Agent - Discovers verified African female tech initiatives and creates IntentMandate.
"""
try:
    from .agent import finding_agent
    root_agent = finding_agent
    __all__ = ["finding_agent", "root_agent"]
except (ImportError, AttributeError):
    __all__ = []
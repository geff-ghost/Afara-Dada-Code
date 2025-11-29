"""
Credentials Provider Agent - Handles payment processing with user consent.
"""
try:
    from .agent import credentials_provider
    root_agent = credentials_provider
    __all__ = ["credentials_provider", "root_agent"]
except (ImportError, AttributeError):
    __all__ = []

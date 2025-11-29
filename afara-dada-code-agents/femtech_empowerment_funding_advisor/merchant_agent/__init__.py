"""
Merchant Agent - Creates W3C-compliant CartMandates for Female Tech Empowerment Initiatives.
"""
try:
    from .agent import merchant_agent
    root_agent = merchant_agent
    __all__ = ["merchant_agent", "root_agent"]
except (ImportError, AttributeError):
    __all__ = []
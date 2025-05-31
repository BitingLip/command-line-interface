"""
CLI Configuration
Uses centralized BitingLip configuration system.
"""

# Import from centralized configuration system
import sys
import os
from enum import Enum
sys.path.append(os.path.join(os.path.dirname(__file__), '../../config'))

from central_config import get_config
from service_discovery import ServiceDiscovery

class OutputFormat(Enum):
    """Output format options"""
    JSON = "json"
    TABLE = "table"
    YAML = "yaml"

class LogLevel(Enum):
    """Log level options"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class CLIConfig:
    """CLI Configuration"""
    
    def __init__(self):
        self.config = get_config('cli')
        self.service_discovery = ServiceDiscovery()
    
    @property
    def output_format(self):
        return 'table'  # Default output format
    
    @property
    def log_level(self):
        return self.config.log_level
    
    @property
    def api_timeout(self):
        return self.config.default_timeout

class CLIManagerSettings(CLIConfig):
    """Alias for backward compatibility"""
    pass

def get_api_url(service_name):
    """Get API URL for a service"""
    service_discovery = ServiceDiscovery()
    return service_discovery.get_service_url(service_name)

def update_config(**kwargs):
    """Update configuration"""
    # This would update the centralized config
    pass

def get_config_info():
    """Get configuration information"""
    return {
        'output_format': config.output_format,
        'log_level': config.log_level,
        'api_timeout': config.api_timeout
    }

# Create default instances
config = CLIConfig()
settings = CLIManagerSettings()

# Export the same interface as before for backward compatibility
__all__ = [
    'CLIConfig', 'OutputFormat', 'LogLevel', 'config', 
    'get_api_url', 'update_config', 'get_config_info',
    'CLIManagerSettings', 'settings'
]

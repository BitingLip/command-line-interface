"""
CLI Configuration Management

Handles configuration settings, environment variables, and API connection settings
for the BitingLip AI Platform CLI.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from enum import Enum


class OutputFormat(str, Enum):
    """Output format options"""
    TABLE = "table"
    JSON = "json"
    YAML = "yaml"
    CSV = "csv"


class LogLevel(str, Enum):
    """Logging level options"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class CLIConfig(BaseSettings):
    """CLI configuration settings"""
    
    # Gateway API Connection
    api_url: str = Field(
        default="http://localhost:8080",
        description="BitingLip Gateway API base URL"
    )
    api_timeout: int = Field(
        default=30,
        description="API request timeout in seconds"
    )
    api_retries: int = Field(
        default=3,
        description="Number of API request retries"
    )
    
    # Authentication
    api_key: Optional[str] = Field(
        default=None,
        description="API authentication key"
    )
    
    # Output Settings
    output_format: OutputFormat = Field(
        default=OutputFormat.TABLE,
        description="Default output format"
    )
    no_color: bool = Field(
        default=False,
        description="Disable colored output"
    )
    quiet: bool = Field(
        default=False,
        description="Suppress non-essential output"
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output"
    )
    
    # Logging
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level"
    )
    log_file: Optional[str] = Field(
        default=None,
        description="Log file path"
    )
    
    # Pagination
    default_page_size: int = Field(
        default=20,
        description="Default page size for paginated results"
    )
    
    # Watch mode
    watch_interval: int = Field(
        default=5,
        description="Watch mode refresh interval in seconds"
    )
    
    # Service Endpoints (discovered through gateway)
    model_manager_url: Optional[str] = Field(
        default=None,
        description="Model Manager service URL (auto-discovered)"
    )
    cluster_manager_url: Optional[str] = Field(
        default=None,
        description="Cluster Manager service URL (auto-discovered)"
    )
    task_manager_url: Optional[str] = Field(
        default=None,
        description="Task Manager service URL (auto-discovered)"
    )
    
    class Config:
        env_prefix = "BITINGLIP_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


def get_api_url(config: CLIConfig, endpoint: str = "") -> str:
    """
    Get full API URL for an endpoint through the gateway
    
    Args:
        config: CLI configuration
        endpoint: API endpoint path
        
    Returns:
        Complete URL
    """
    base_url = config.api_url.rstrip("/")
    if endpoint:
        endpoint = endpoint.lstrip("/")
        return f"{base_url}/{endpoint}"
    return base_url

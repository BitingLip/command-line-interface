"""
CLI Utility Functions

Common utility functions for the BitingLip CLI.
"""

import json
import click
from typing import Any, Dict, Optional
import structlog

from .client import BitingLipAPIError

logger = structlog.get_logger(__name__)


def format_json(data: Any, indent: int = 2) -> str:
    """Format data as pretty JSON string"""
    return json.dumps(data, indent=indent, ensure_ascii=False)


def success_message(message: str) -> None:
    """Display a success message in green"""
    click.echo(click.style(f"✓ {message}", fg='green'))


def error_message(message: str) -> None:
    """Display an error message in red"""
    click.echo(click.style(f"✗ {message}", fg='red'), err=True)


def warning_message(message: str) -> None:
    """Display a warning message in yellow"""
    click.echo(click.style(f"⚠ {message}", fg='yellow'))


def info_message(message: str) -> None:
    """Display an info message in blue"""
    click.echo(click.style(f"ℹ {message}", fg='blue'))


def handle_api_error(error: BitingLipAPIError) -> None:
    """Handle API errors with appropriate formatting"""
    if error.status_code:
        error_message(f"API Error ({error.status_code}): {error}")
    else:
        error_message(f"API Error: {error}")
    
    if error.response and isinstance(error.response, dict):
        if 'detail' in error.response:
            click.echo(f"Details: {error.response['detail']}", err=True)
        elif 'message' in error.response:
            click.echo(f"Message: {error.response['message']}", err=True)


def confirm_action(message: str, default: bool = False) -> bool:
    """Prompt user for confirmation"""
    return click.confirm(message, default=default)


def prompt_for_input(prompt: str, default: Optional[str] = None, hide_input: bool = False) -> str:
    """Prompt user for input"""
    return click.prompt(prompt, default=default, hide_input=hide_input)


def validate_json_string(value: str) -> Dict[str, Any]:
    """Validate and parse JSON string"""
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise click.BadParameter(f"Invalid JSON: {str(e)}")


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_file_size(bytes_size: int) -> str:
    """Format file size in bytes to human readable format"""
    size = float(bytes_size)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}PB"


def truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate string to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def format_timestamp(timestamp: str) -> str:
    """Format ISO timestamp to readable format"""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError):
        return timestamp


def parse_key_value_pairs(pairs: list) -> Dict[str, str]:
    """Parse key=value pairs from command line arguments"""
    result = {}
    for pair in pairs:
        if '=' not in pair:
            raise click.BadParameter(f"Invalid key=value pair: {pair}")
        key, value = pair.split('=', 1)
        result[key.strip()] = value.strip()
    return result


def print_table_with_pagination(data: list, headers: list, page_size: int = 20):
    """Print table with pagination support"""
    from tabulate import tabulate
    
    if not data:
        click.echo("No data to display.")
        return
    
    total_pages = (len(data) + page_size - 1) // page_size
    current_page = 1
    
    while True:
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, len(data))
        page_data = data[start_idx:end_idx]
        
        click.echo(tabulate(page_data, headers=headers, tablefmt='grid'))
        click.echo(f"\nPage {current_page} of {total_pages} (showing {len(page_data)} of {len(data)} items)")
        
        if current_page >= total_pages:
            break
            
        if not click.confirm("\nShow next page?", default=True):
            break
            
        current_page += 1


def setup_logging(verbose: bool = False):
    """Setup structured logging for CLI"""
    import structlog
    
    level = "DEBUG" if verbose else "INFO"
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

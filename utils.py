"""
CLI Utility Functions

Common utilities for formatting output, handling data, and user interactions.
"""

import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from tabulate import tabulate
import structlog
import click
import requests

from .config import config, OutputFormat


def handle_api_error(error: Exception, context: str = "API operation") -> None:
    """
    Handle and display API errors in a user-friendly way
    
    Args:
        error: The exception that occurred
        context: Context description for the error
    """
    logger = structlog.get_logger()
    
    error_msg = str(error)    # Handle specific error types
    if isinstance(error, requests.HTTPError) and hasattr(error, 'response') and error.response is not None:
        # HTTP error with response
        try:
            response_data = error.response.json()
            error_msg = response_data.get('detail', error_msg)
        except:
            error_msg = f"HTTP {error.response.status_code}: {error.response.reason}"
    
    elif "connection" in error_msg.lower():
        error_msg = "Could not connect to API server. Please check if the server is running."
    
    elif "timeout" in error_msg.lower():
        error_msg = "Request timed out. The server may be overloaded."
    
    # Log the full error for debugging
    logger.error(context, error=str(error))
    
    # Display user-friendly error
    click.echo(click.style(f"❌ {context} failed: {error_msg}", fg='red'), err=True)


logger = structlog.get_logger(__name__)


def format_output(
    data: Union[Dict, List, str], 
    output_format: Optional[OutputFormat] = None,
    table_headers: Optional[List[str]] = None
) -> str:
    """
    Format data for output based on specified format
    
    Args:
        data: Data to format
        output_format: Output format (defaults to config)
        table_headers: Headers for table format
        
    Returns:
        Formatted string    """
    fmt = output_format or config.output_format
    
    if fmt == OutputFormat.JSON:
        return json.dumps(data, indent=2, default=str)
    
    elif fmt == OutputFormat.TABLE:
        if isinstance(data, str):
            return data
        return format_table(data, table_headers)
    
    elif fmt == OutputFormat.CSV:
        if isinstance(data, str):
            return data
        return format_csv(data, table_headers)
    
    elif fmt == OutputFormat.YAML:
        try:
            import yaml
            return yaml.dump(data, default_flow_style=False)
        except ImportError:
            logger.warning("PyYAML not installed, falling back to JSON")
            return json.dumps(data, indent=2, default=str)
    
    else:
        return str(data)


def format_table(data: Union[Dict, List], headers: Optional[List[str]] = None) -> str:
    """
    Format data as a table
    
    Args:
        data: Data to format
        headers: Table headers
        
    Returns:
        Formatted table string
    """
    if not data:
        return "No data available"
    
    if isinstance(data, dict):
        # Convert dict to key-value table
        table_data = [[k, v] for k, v in data.items()]
        headers = headers or ["Key", "Value"]
    
    elif isinstance(data, list):
        if not data:
            return "No data available"
        
        if isinstance(data[0], dict):
            # List of dictionaries - convert to table
            if not headers:
                headers = list(data[0].keys())
            table_data = [[item.get(h, "") for h in headers] for item in data]
        else:
            # List of values
            table_data = [[item] for item in data]
            headers = headers or ["Value"]
    
    else:
        return str(data)
    
    return tabulate(table_data, headers=headers, tablefmt="grid")


def format_csv(data: Union[Dict, List], headers: Optional[List[str]] = None) -> str:
    """
    Format data as CSV
    
    Args:
        data: Data to format
        headers: CSV headers
        
    Returns:
        CSV formatted string
    """
    import csv
    import io
    
    output = io.StringIO()
    
    if isinstance(data, dict):
        headers = headers or ["Key", "Value"]
        writer = csv.writer(output)
        writer.writerow(headers)
        for k, v in data.items():
            writer.writerow([k, v])
    
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        headers = headers or list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for item in data:
            writer.writerow(item)
    
    else:
        writer = csv.writer(output)
        if headers:
            writer.writerow(headers)
        if isinstance(data, list):
            for item in data:
                writer.writerow([item])
        else:
            writer.writerow([data])
    
    return output.getvalue()


def print_output(
    data: Any, 
    output_format: Optional[OutputFormat] = None,
    headers: Optional[List[str]] = None,
    title: Optional[str] = None
) -> None:
    """
    Print formatted output to stdout
    
    Args:
        data: Data to print
        output_format: Output format
        headers: Table headers
        title: Optional title
    """
    if config.quiet and not config.verbose:
        return
    
    if title and not config.quiet:
        print_title(title)
    
    formatted = format_output(data, output_format, headers)
    print(formatted)


def print_title(title: str, char: str = "=") -> None:
    """Print a formatted title"""
    if config.quiet:
        return
    
    print()
    print(title)
    print(char * len(title))


def print_error(message: str, exit_code: int = 1) -> None:
    """
    Print error message and optionally exit
    
    Args:
        message: Error message
        exit_code: Exit code (0 to not exit)
    """
    error_msg = f"Error: {message}"
    if config.no_color:
        print(error_msg, file=sys.stderr)
    else:
        try:
            from rich.console import Console
            console = Console(stderr=True)
            console.print(error_msg, style="red bold")
        except ImportError:
            print(error_msg, file=sys.stderr)
    
    if exit_code > 0:
        sys.exit(exit_code)


def print_success(message: str) -> None:
    """Print success message"""
    if config.quiet:
        return
    
    if config.no_color:
        print(f"Success: {message}")
    else:
        try:
            from rich.console import Console
            console = Console()
            console.print(f"Success: {message}", style="green bold")
        except ImportError:
            print(f"Success: {message}")


def print_warning(message: str) -> None:
    """Print warning message"""
    if config.quiet:
        return
    
    if config.no_color:
        print(f"Warning: {message}")
    else:
        try:
            from rich.console import Console
            console = Console()
            console.print(f"Warning: {message}", style="yellow bold")
        except ImportError:
            print(f"Warning: {message}")


def print_info(message: str) -> None:
    """Print info message"""
    if config.quiet or not config.verbose:
        return
    
    print(f"Info: {message}")


def format_bytes(bytes_value: float) -> str:
    """
    Format bytes in human readable format
    
    Args:
        bytes_value: Bytes value
        
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration in human readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.1f}s"
    
    hours = int(minutes // 60)
    remaining_minutes = minutes % 60
    
    return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"


def format_timestamp(timestamp: Union[str, datetime]) -> str:
    """
    Format timestamp for display
    
    Args:
        timestamp: Timestamp string or datetime object
        
    Returns:
        Formatted timestamp string
    """
    if isinstance(timestamp, str):
        try:
            # Try parsing ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            return timestamp
    else:
        dt = timestamp
    
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_key_value_pairs(pairs: List[str]) -> Dict[str, str]:
    """
    Parse key=value pairs from command line
    
    Args:
        pairs: List of "key=value" strings
        
    Returns:
        Dictionary of parsed pairs
    """
    result = {}
    for pair in pairs:
        if '=' not in pair:
            logger.warning(f"Invalid key=value pair: {pair}")
            continue
        
        key, value = pair.split('=', 1)
        result[key.strip()] = value.strip()
    
    return result


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation
    
    Args:
        message: Confirmation message
        default: Default choice if user just presses enter
        
    Returns:
        True if confirmed, False otherwise
    """
    if config.quiet:
        return default
    
    prompt = f"{message} ({'Y/n' if default else 'y/N'}): "
    
    try:
        response = input(prompt).strip().lower()
        if not response:
            return default
        return response in ['y', 'yes', 'true', '1']
    except (KeyboardInterrupt, EOFError):
        print()
        return False


def wait_for_completion(
    check_func,
    check_interval: int = 2,
    max_wait: int = 300,
    progress_callback: Optional[Callable] = None
) -> bool:
    """
    Wait for an operation to complete
    
    Args:
        check_func: Function that returns True when complete
        check_interval: Check interval in seconds
        max_wait: Maximum wait time in seconds
        progress_callback: Optional progress callback
        
    Returns:
        True if completed, False if timed out
    """
    start_time = datetime.now()
    
    while True:
        if check_func():
            return True
        
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed >= max_wait:
            return False
        
        if progress_callback:
            progress_callback(elapsed, max_wait)
        
        time.sleep(check_interval)

#!/usr/bin/env python3
"""
BitingLip CLI - Main Entry Point

Command-line interface for the BitingLip AI inference platform.
Provides unified access to all BitingLip services through the gateway.
"""

import sys
import os
from pathlib import Path

# Add the CLI package to Python path
cli_root = Path(__file__).parent
sys.path.insert(0, str(cli_root))

import click
import structlog
from typing import Optional

from cli.config import CLIConfig, OutputFormat
from cli.commands.models import models_command
from cli.commands.workers import workers_command
from cli.commands.tasks import tasks_command
from cli.commands.cluster import cluster_command
from cli.commands.system import system_command

# Configure structured logging
logger = structlog.get_logger()


@click.group()
@click.option(
    '--api-url', 
    help='Gateway API base URL (default: http://localhost:8080)',
    envvar='BITINGLIP_API_URL'
)
@click.option(
    '--timeout', 
    type=int, 
    help='Request timeout in seconds (default: 30)',
    envvar='BITINGLIP_TIMEOUT'
)
@click.option(
    '--format', 
    'output_format', 
    type=click.Choice(['table', 'json', 'csv', 'yaml']), 
    help='Output format (default: table)',
    envvar='BITINGLIP_FORMAT'
)
@click.option(
    '--verbose', 
    '-v', 
    is_flag=True, 
    help='Enable verbose output',
    envvar='BITINGLIP_VERBOSE'
)
@click.option(
    '--quiet', 
    '-q', 
    is_flag=True, 
    help='Suppress non-essential output',
    envvar='BITINGLIP_QUIET'
)
@click.option(
    '--api-key',
    help='API authentication key',
    envvar='BITINGLIP_API_KEY'
)
@click.pass_context
def cli(ctx: click.Context, api_url: Optional[str], timeout: Optional[int], 
        output_format: Optional[str], verbose: bool, quiet: bool, api_key: Optional[str]):
    """
    BitingLip AI Platform CLI
    
    Command-line interface for managing the BitingLip distributed AI inference platform.
    Provides unified access to cluster management, model operations, worker monitoring,
    and task orchestration through the gateway manager.
    
    Examples:
        # Check system status
        bitinglip system status
        
        # List all available models
        bitinglip models list
        
        # Download a new model
        bitinglip models download microsoft/DialoGPT-medium
        
        # Monitor cluster health
        bitinglip cluster status
        
        # List active workers
        bitinglip workers list --status online
        
        # Monitor running tasks
        bitinglip tasks list --status running
    
    Environment Variables:
        BITINGLIP_API_URL     Gateway API base URL
        BITINGLIP_API_KEY     API authentication key
        BITINGLIP_FORMAT      Default output format
        BITINGLIP_TIMEOUT     Request timeout
        BITINGLIP_VERBOSE     Enable verbose output
        BITINGLIP_QUIET       Suppress non-essential output
    """    # Ensure context object exists
    ctx.ensure_object(CLIConfig)
    
    # Load configuration
    config = ctx.obj
    
    # Override config with command-line options
    if api_url:
        config.api_url = api_url
    if timeout:
        config.api_timeout = timeout
    if output_format:
        config.output_format = OutputFormat(output_format)
    if verbose:
        config.verbose = True
    if quiet:
        config.quiet = True
    if api_key:
        config.api_key = api_key
    
    # Configure logging level
    if verbose:
        structlog.configure(
            processors=[
                structlog.dev.ConsoleRenderer(colors=True)
            ],
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
            cache_logger_on_first_use=True,
        )
    elif quiet:
        structlog.configure(
            processors=[
                structlog.dev.ConsoleRenderer(colors=False)
            ],
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.make_filtering_bound_logger(40),  # ERROR level
            cache_logger_on_first_use=True,
        )


@click.command()
@click.pass_context
def version(ctx: click.Context):
    """Show CLI version information."""
    click.echo("BitingLip AI Platform CLI v1.0.0")
    config = ctx.obj
    click.echo(f"Gateway URL: {config.api_url}")
    click.echo(f"Output Format: {config.output_format.value}")


# Add command groups
cli.add_command(system_command)
cli.add_command(cluster_command)
cli.add_command(models_command)
cli.add_command(workers_command)
cli.add_command(tasks_command)
cli.add_command(version)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.", err=True)
        raise click.Abort()
    except Exception as e:
        logger.error("Unexpected error occurred", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()

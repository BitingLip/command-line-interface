#!/usr/bin/env python3
"""
Main CLI entry point for the AMD GPU Cluster Model Management System.
"""

import click
import structlog
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import CLIConfig, OutputFormat
from commands import cluster, models, workers, health

# Configure structured logging
logger = structlog.get_logger()


@click.group()
@click.option('--api-url', help='API base URL (default: http://localhost:8080)')
@click.option('--timeout', type=int, help='Request timeout in seconds (default: 30)')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'csv', 'yaml']), 
              help='Output format (default: table)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-essential output')
@click.pass_context
def cli(ctx: click.Context, api_url: Optional[str], timeout: Optional[int], 
        output_format: Optional[str], verbose: bool, quiet: bool):
    """
    AMD GPU Cluster Model Management CLI
    
    Command-line interface for managing the distributed model inference cluster.
    Provides tools for model management, worker monitoring, and system health checks.
    
    Examples:
        # List all available models
        cli models list
        
        # Download a new model
        cli models download --model-id microsoft/DialoGPT-medium
        
        # Check cluster health
        cli health status
        
        # Monitor worker status
        cli workers list --status online
    """
    
    # Validate mutually exclusive options
    if verbose and quiet:
        raise click.UsageError("--verbose and --quiet options are mutually exclusive")
      # Initialize CLI configuration
    ctx.ensure_object(dict)
    ctx.obj['config'] = CLIConfig(
        api_url=api_url or "http://localhost:8080",
        api_timeout=timeout or 30,
        output_format=OutputFormat(output_format) if output_format else OutputFormat.TABLE
    )
    
    # Configure logging level based on verbosity
    if verbose:
        logger.info("Verbose mode enabled")
    elif quiet:
        logger.info("Quiet mode enabled")


# Register command groups
cli.add_command(models.models, name='models')
cli.add_command(workers.workers, name='workers')
cli.add_command(cluster.cluster, name='cluster')
cli.add_command(health.health, name='health')


if __name__ == '__main__':
    cli()

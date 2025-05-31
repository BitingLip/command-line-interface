#!/usr/bin/env python3
"""
Main CLI entry point for the AMD GPU Cluster Model Management System.
"""

import click
import structlog
from typing import Optional

from .config import CLIConfig, OutputFormat
from .commands import cluster, models, workers, health

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
    Provides administrative and operational commands for cluster operators.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Load configuration
    config = CLIConfig()
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
    
    # Store config in context
    ctx.obj['config'] = config
    
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
    click.echo("AMD GPU Cluster Model Management CLI v1.0.0")
    config = ctx.obj['config']
    click.echo(f"API URL: {config.api_url}")


# Add command groups
cli.add_command(cluster.cluster)
cli.add_command(models.models)
cli.add_command(workers.workers)
cli.add_command(health.health)
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

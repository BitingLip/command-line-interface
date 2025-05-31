"""
System Management Commands

Commands for system-wide operations in the BitingLip platform.
All operations are routed through the gateway.
"""

import click
import json
from typing import Optional
from tabulate import tabulate
import structlog

from ..client import BitingLipClient, BitingLipAPIError
from ..config import CLIConfig
from ..utils import format_json, handle_api_error, success_message, error_message, format_timestamp

logger = structlog.get_logger(__name__)


@click.group()
@click.pass_context
def system_command(ctx):
    """System-wide operations and monitoring"""
    pass


@system_command.command('status')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def system_status(ctx, output_format: str):
    """Show overall system status"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            status = client.get_system_status()
            
            if output_format == 'json':
                click.echo(format_json(status))
            else:
                click.echo("BitingLip System Status")
                click.echo("=" * 30)
                
                # General information
                general = status.get('general', {})
                if general:
                    rows = []
                    rows.append(['System Version', general.get('version', 'N/A')])
                    rows.append(['Status', general.get('status', 'N/A')])
                    rows.append(['Uptime', general.get('uptime', 'N/A')])
                    rows.append(['Environment', general.get('environment', 'N/A')])
                    rows.append(['Started At', format_timestamp(general.get('started_at', 'N/A'))])
                    
                    click.echo(tabulate(rows, headers=['Property', 'Value'], tablefmt='grid'))
                    click.echo()
                
                # Service status
                services = status.get('services', {})
                if services:
                    click.echo("Service Status:")
                    headers = ['Service', 'Status', 'Version', 'Uptime']
                    rows = []
                    for service_name, service_info in services.items():
                        rows.append([
                            service_name,
                            service_info.get('status', 'Unknown'),
                            service_info.get('version', 'N/A'),
                            service_info.get('uptime', 'N/A')
                        ])
                    
                    click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                    click.echo()
                
                # Quick stats
                stats = status.get('stats', {})
                if stats:
                    click.echo("Quick Statistics:")
                    rows = []
                    rows.append(['Total Models', stats.get('total_models', 0)])
                    rows.append(['Active Workers', stats.get('active_workers', 0)])
                    rows.append(['Running Tasks', stats.get('running_tasks', 0)])
                    rows.append(['Completed Tasks (24h)', stats.get('completed_tasks_24h', 0)])
                    
                    click.echo(tabulate(rows, headers=['Metric', 'Value'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get system status: {str(e)}")


@system_command.command('health')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.option('--detailed', is_flag=True, help='Show detailed health information')
@click.pass_context
def system_health(ctx, output_format: str, detailed: bool):
    """Check system health"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            health = client.get_health_check()
            
            if output_format == 'json':
                click.echo(format_json(health))
            else:
                # Overall health status
                overall_status = health.get('status', 'Unknown')
                color = 'green' if overall_status == 'healthy' else 'red' if overall_status == 'unhealthy' else 'yellow'
                
                click.echo("BitingLip System Health")
                click.echo("=" * 30)
                click.echo(f"Overall Status: {click.style(overall_status.upper(), fg=color)}")
                click.echo(f"Timestamp: {format_timestamp(health.get('timestamp', ''))}")
                click.echo()
                
                # Component health
                components = health.get('components', {})
                if components:
                    click.echo("Component Health:")
                    headers = ['Component', 'Status', 'Response Time', 'Message']
                    rows = []
                    for comp_name, comp_health in components.items():
                        rows.append([
                            comp_name,
                            comp_health.get('status', 'Unknown'),
                            f"{comp_health.get('response_time_ms', 0)}ms",
                            comp_health.get('message', '')[:50] + '...' if len(comp_health.get('message', '')) > 50 else comp_health.get('message', '')
                        ])
                    
                    click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                    click.echo()
                
                # Detailed information
                if detailed:
                    details = health.get('details', {})
                    if details:
                        click.echo("Detailed Health Information:")
                        for comp_name, comp_details in details.items():
                            click.echo(f"\n{comp_name}:")
                            for key, value in comp_details.items():
                                if isinstance(value, (dict, list)):
                                    value = json.dumps(value, indent=2)
                                click.echo(f"  {key}: {value}")
                
                # Health checks summary
                checks = health.get('checks', {})
                if checks:
                    passed = sum(1 for check in checks.values() if check.get('status') == 'pass')
                    total = len(checks)
                    click.echo(f"Health Checks: {passed}/{total} passed")
                    
                    if passed < total:
                        click.echo("\nFailed Checks:")
                        for check_name, check_result in checks.items():
                            if check_result.get('status') != 'pass':
                                click.echo(f"  ✗ {check_name}: {check_result.get('message', 'Unknown error')}")
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get system health: {str(e)}")


@system_command.command('info')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def system_info(ctx, output_format: str):
    """Show system information"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            # Gather information from multiple endpoints
            system_status = client.get_system_status()
            health_check = client.get_health_check()
            cluster_status = client.get_cluster_status()
            
            info = {
                'system': system_status.get('general', {}),
                'services': system_status.get('services', {}),
                'cluster': cluster_status.get('general', {}),
                'health': health_check.get('status', 'Unknown'),
                'configuration': {
                    'api_url': config.api_url,
                    'timeout': config.api_timeout,
                    'retries': config.api_retries,
                    'environment': config.environment
                }
            }
            
            if output_format == 'json':
                click.echo(format_json(info))
            else:
                click.echo("BitingLip System Information")
                click.echo("=" * 40)
                
                # System overview
                system = info.get('system', {})
                if system:
                    click.echo("System Overview:")
                    rows = []
                    rows.append(['Version', system.get('version', 'N/A')])
                    rows.append(['Environment', system.get('environment', 'N/A')])
                    rows.append(['Health Status', info.get('health', 'N/A')])
                    rows.append(['Uptime', system.get('uptime', 'N/A')])
                    
                    click.echo(tabulate(rows, headers=['Property', 'Value'], tablefmt='grid'))
                    click.echo()
                
                # Service summary
                services = info.get('services', {})
                if services:
                    click.echo("Services:")
                    headers = ['Service', 'Status', 'Version']
                    rows = []
                    for service_name, service_info in services.items():
                        rows.append([
                            service_name,
                            service_info.get('status', 'Unknown'),
                            service_info.get('version', 'N/A')
                        ])
                    
                    click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                    click.echo()
                
                # Cluster summary
                cluster = info.get('cluster', {})
                if cluster:
                    click.echo("Cluster:")
                    rows = []
                    rows.append(['Cluster Name', cluster.get('cluster_name', 'N/A')])
                    rows.append(['Total Nodes', cluster.get('total_nodes', 0)])
                    rows.append(['Active Workers', cluster.get('active_workers', 0)])
                    
                    click.echo(tabulate(rows, headers=['Property', 'Value'], tablefmt='grid'))
                    click.echo()
                
                # Configuration
                config_info = info.get('configuration', {})
                if config_info:
                    click.echo("Client Configuration:")
                    rows = []
                    for key, value in config_info.items():
                        rows.append([key.replace('_', ' ').title(), str(value)])
                    
                    click.echo(tabulate(rows, headers=['Setting', 'Value'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get system information: {str(e)}")


@system_command.command('logs')
@click.option('--service', help='Filter by service name')
@click.option('--level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), 
              help='Filter by log level')
@click.option('--tail', type=int, default=100, help='Number of recent log lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.pass_context
def system_logs(ctx, service: Optional[str], level: Optional[str], tail: int, follow: bool):
    """Show system logs"""
    config = ctx.obj
    
    try:
        # For now, show a placeholder message
        # In a real implementation, this would stream logs from the services
        click.echo("System Logs")
        click.echo("=" * 20)
        
        if service:
            click.echo(f"Service: {service}")
        if level:
            click.echo(f"Level: {level}")
        click.echo(f"Showing last {tail} lines")
        if follow:
            click.echo("Following log output...")
        click.echo()
        
        click.echo("Note: Log streaming is not yet implemented.")
        click.echo("Use service-specific logs or check individual service endpoints.")
        
        # TODO: Implement actual log streaming
        # This would involve:
        # 1. Connecting to log aggregation system
        # 2. Streaming logs in real-time
        # 3. Filtering by service and level
        # 4. Proper formatting and coloring
        
    except Exception as e:
        error_message(f"Failed to get system logs: {str(e)}")


@system_command.command('version')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def system_version(ctx, output_format: str):
    """Show version information for all components"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            status = client.get_system_status()
            services = status.get('services', {})
            
            versions = {
                'cli': '1.0.0',  # CLI version
                'system': status.get('general', {}).get('version', 'N/A')
            }
            
            # Add service versions
            for service_name, service_info in services.items():
                versions[service_name] = service_info.get('version', 'N/A')
            
            if output_format == 'json':
                click.echo(format_json(versions))
            else:
                click.echo("BitingLip Version Information")
                click.echo("=" * 35)
                
                rows = []
                for component, version in versions.items():
                    rows.append([component.replace('_', '-').title(), version])
                
                click.echo(tabulate(rows, headers=['Component', 'Version'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get version information: {str(e)}")

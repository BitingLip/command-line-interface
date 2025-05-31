"""
Cluster Management Commands

Commands for managing the BitingLip cluster.
All operations are routed through the gateway to cluster-manager.
"""

import click
import json
from typing import Optional
from tabulate import tabulate
import structlog

from ..client import BitingLipClient, BitingLipAPIError
from ..config import CLIConfig
from ..utils import format_json, handle_api_error, success_message, error_message

logger = structlog.get_logger(__name__)


@click.group()
@click.pass_context
def cluster_command(ctx):
    """Manage the BitingLip cluster"""
    pass


@cluster_command.command('status')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def cluster_status(ctx, output_format: str):
    """Show cluster status"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            status = client.get_cluster_status()
            
            if output_format == 'json':
                click.echo(format_json(status))
            else:
                # Display cluster overview
                click.echo("BitingLip Cluster Status")
                click.echo("=" * 30)
                
                # General status
                general = status.get('general', {})
                if general:
                    rows = []
                    rows.append(['Cluster Name', general.get('cluster_name', 'N/A')])
                    rows.append(['Status', general.get('status', 'N/A')])
                    rows.append(['Uptime', general.get('uptime', 'N/A')])
                    rows.append(['Total Nodes', general.get('total_nodes', 0)])
                    rows.append(['Active Nodes', general.get('active_nodes', 0)])
                    
                    click.echo(tabulate(rows, headers=['Property', 'Value'], tablefmt='grid'))
                
                # Worker statistics
                worker_stats = status.get('worker_stats', {})
                if worker_stats:
                    click.echo("\nWorker Statistics:")
                    rows = []
                    rows.append(['Total Workers', worker_stats.get('total_workers', 0)])
                    rows.append(['Active Workers', worker_stats.get('active_workers', 0)])
                    rows.append(['Busy Workers', worker_stats.get('busy_workers', 0)])
                    rows.append(['Load', f"{worker_stats.get('total_load', 0)}/{worker_stats.get('total_capacity', 0)}"])
                    
                    click.echo(tabulate(rows, headers=['Metric', 'Value'], tablefmt='grid'))
                
                # Task statistics
                task_stats = status.get('task_stats', {})
                if task_stats:
                    click.echo("\nTask Statistics:")
                    rows = []
                    rows.append(['Total Tasks', task_stats.get('total_tasks', 0)])
                    rows.append(['Running Tasks', task_stats.get('running_tasks', 0)])
                    rows.append(['Completed Tasks', task_stats.get('completed_tasks', 0)])
                    rows.append(['Failed Tasks', task_stats.get('failed_tasks', 0)])
                    
                    click.echo(tabulate(rows, headers=['Metric', 'Value'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get cluster status: {str(e)}")


@cluster_command.command('health')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def cluster_health(ctx, output_format: str):
    """Check cluster health"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            health = client.get_cluster_health()
            
            if output_format == 'json':
                click.echo(format_json(health))
            else:
                click.echo("BitingLip Cluster Health")
                click.echo("=" * 30)
                
                # Overall health
                overall = health.get('overall', {})
                if overall:
                    status = overall.get('status', 'Unknown')
                    color = 'green' if status == 'healthy' else 'red' if status == 'unhealthy' else 'yellow'
                    click.echo(f"Overall Status: {click.style(status.upper(), fg=color)}")
                    click.echo(f"Last Check: {overall.get('last_check', 'N/A')}")
                    click.echo()
                
                # Service health
                services = health.get('services', {})
                if services:
                    click.echo("Service Health:")
                    headers = ['Service', 'Status', 'Last Check', 'Issues']
                    rows = []
                    for service_name, service_health in services.items():
                        rows.append([
                            service_name,
                            service_health.get('status', 'Unknown'),
                            service_health.get('last_check', 'N/A'),
                            len(service_health.get('issues', []))
                        ])
                    
                    click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                    click.echo()
                
                # Worker health
                workers = health.get('workers', {})
                if workers:
                    click.echo("Worker Health:")
                    headers = ['Worker ID', 'Status', 'Health', 'Issues']
                    rows = []
                    for worker_id, worker_health in workers.items():
                        rows.append([
                            worker_id[:12] + '...' if len(worker_id) > 12 else worker_id,
                            worker_health.get('status', 'Unknown'),
                            worker_health.get('health_status', 'Unknown'),
                            len(worker_health.get('issues', []))
                        ])
                    
                    click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                
                # Show issues if any
                all_issues = []
                for service_health in services.values():
                    all_issues.extend(service_health.get('issues', []))
                for worker_health in workers.values():
                    all_issues.extend(worker_health.get('issues', []))
                
                if all_issues:
                    click.echo("\nIssues Found:")
                    for i, issue in enumerate(all_issues[:10], 1):  # Show first 10 issues
                        click.echo(f"{i}. {issue}")
                    if len(all_issues) > 10:
                        click.echo(f"... and {len(all_issues) - 10} more issues")
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get cluster health: {str(e)}")


@cluster_command.command('nodes')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def cluster_nodes(ctx, output_format: str):
    """List cluster nodes"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            # Get cluster status to find node information
            status = client.get_cluster_status()
            nodes = status.get('nodes', [])
            
            if output_format == 'json':
                click.echo(format_json(nodes))
            else:
                if not nodes:
                    click.echo("No cluster nodes found.")
                    return
                
                headers = ['Node ID', 'Type', 'Status', 'Address', 'Workers', 'Load']
                rows = []
                for node in nodes:
                    rows.append([
                        node.get('id', 'N/A')[:12] + '...',
                        node.get('type', 'N/A'),
                        node.get('status', 'N/A'),
                        f"{node.get('host', 'N/A')}:{node.get('port', 'N/A')}",
                        node.get('worker_count', 0),
                        f"{node.get('current_load', 0)}/{node.get('max_load', 1)}"
                    ])
                
                click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to list cluster nodes: {str(e)}")


@cluster_command.command('resources')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def cluster_resources(ctx, output_format: str):
    """Show cluster resource usage"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            status = client.get_cluster_status()
            resources = status.get('resources', {})
            
            if output_format == 'json':
                click.echo(format_json(resources))
            else:
                if not resources:
                    click.echo("No resource information available.")
                    return
                
                click.echo("Cluster Resource Usage")
                click.echo("=" * 30)
                
                # CPU usage
                cpu = resources.get('cpu', {})
                if cpu:
                    click.echo("CPU Usage:")
                    rows = []
                    rows.append(['Total CPUs', cpu.get('total_cpus', 'N/A')])
                    rows.append(['Used CPUs', cpu.get('used_cpus', 'N/A')])
                    rows.append(['Usage %', f"{cpu.get('usage_percent', 0):.1f}%"])
                    click.echo(tabulate(rows, headers=['Metric', 'Value'], tablefmt='grid'))
                    click.echo()
                
                # Memory usage
                memory = resources.get('memory', {})
                if memory:
                    click.echo("Memory Usage:")
                    rows = []
                    rows.append(['Total Memory', memory.get('total_memory', 'N/A')])
                    rows.append(['Used Memory', memory.get('used_memory', 'N/A')])
                    rows.append(['Available Memory', memory.get('available_memory', 'N/A')])
                    rows.append(['Usage %', f"{memory.get('usage_percent', 0):.1f}%"])
                    click.echo(tabulate(rows, headers=['Metric', 'Value'], tablefmt='grid'))
                    click.echo()
                
                # GPU usage
                gpu = resources.get('gpu', {})
                if gpu:
                    click.echo("GPU Usage:")
                    rows = []
                    rows.append(['Total GPUs', gpu.get('total_gpus', 'N/A')])
                    rows.append(['Used GPUs', gpu.get('used_gpus', 'N/A')])
                    rows.append(['Usage %', f"{gpu.get('usage_percent', 0):.1f}%"])
                    click.echo(tabulate(rows, headers=['Metric', 'Value'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get cluster resources: {str(e)}")


@cluster_command.command('metrics')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.option('--period', default='1h', help='Time period for metrics (e.g., 1h, 24h, 7d)')
@click.pass_context
def cluster_metrics(ctx, output_format: str, period: str):
    """Show cluster performance metrics"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            # For now, just show current status - in a real implementation
            # this would fetch historical metrics
            status = client.get_cluster_status()
            metrics = status.get('metrics', {})
            
            if output_format == 'json':
                click.echo(format_json(metrics))
            else:
                click.echo(f"Cluster Metrics (Period: {period})")
                click.echo("=" * 40)
                
                if not metrics:
                    click.echo("No metrics available.")
                    click.echo("Note: Historical metrics collection is not yet implemented.")
                    return
                
                # Performance metrics
                perf = metrics.get('performance', {})
                if perf:
                    click.echo("Performance Metrics:")
                    rows = []
                    rows.append(['Avg Response Time', f"{perf.get('avg_response_time', 0):.2f}ms"])
                    rows.append(['Tasks/Hour', perf.get('tasks_per_hour', 0)])
                    rows.append(['Success Rate', f"{perf.get('success_rate', 0):.1f}%"])
                    rows.append(['Error Rate', f"{perf.get('error_rate', 0):.1f}%"])
                    
                    click.echo(tabulate(rows, headers=['Metric', 'Value'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get cluster metrics: {str(e)}")

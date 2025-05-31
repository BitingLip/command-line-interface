"""
Worker Management Commands

Commands for managing workers in the BitingLip cluster.
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
def workers_command(ctx):
    """Manage workers in the BitingLip cluster"""
    pass


@workers_command.command('list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.option('--status', help='Filter by worker status')
@click.option('--type', 'worker_type', help='Filter by worker type')
@click.pass_context
def list_workers(ctx, output_format: str, status: Optional[str], worker_type: Optional[str]):
    """List all workers"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            params = {}
            if status:
                params['status'] = status
            if worker_type:
                params['type'] = worker_type
                
            response = client.list_workers(**params)
            workers = response.get('workers', [])
            
            if output_format == 'json':
                click.echo(format_json(workers))
            else:
                if not workers:
                    click.echo("No workers found.")
                    return
                
                headers = ['ID', 'Name', 'Status', 'Type', 'Load', 'Models', 'Last Seen']
                rows = []
                for worker in workers:
                    rows.append([
                        worker.get('id', 'N/A'),
                        worker.get('name', 'N/A'),
                        worker.get('status', 'N/A'),
                        worker.get('type', 'N/A'),
                        f"{worker.get('current_load', 0)}/{worker.get('max_load', 1)}",
                        len(worker.get('assigned_models', [])),
                        worker.get('last_heartbeat', 'N/A')
                    ])
                
                click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to list workers: {str(e)}")


@workers_command.command('show')
@click.argument('worker_id')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def show_worker(ctx, worker_id: str, output_format: str):
    """Show detailed information about a worker"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            worker = client.get_worker(worker_id)
            
            if output_format == 'json':
                click.echo(format_json(worker))
            else:
                # Display as key-value table
                rows = []
                for key, value in worker.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, indent=2)
                    rows.append([key.replace('_', ' ').title(), str(value)])
                
                click.echo(tabulate(rows, headers=['Property', 'Value'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get worker: {str(e)}")


@workers_command.command('register')
@click.argument('name')
@click.option('--type', 'worker_type', default='general', help='Worker type')
@click.option('--host', help='Worker host address')
@click.option('--port', type=int, help='Worker port')
@click.option('--max-load', type=int, default=1, help='Maximum concurrent load')
@click.option('--capabilities', help='Worker capabilities as JSON array')
@click.option('--metadata', help='Additional metadata as JSON string')
@click.pass_context
def register_worker(ctx, name: str, worker_type: str, host: Optional[str], 
                   port: Optional[int], max_load: int, capabilities: Optional[str],
                   metadata: Optional[str]):
    """Register a new worker"""
    config = ctx.obj
    
    try:
        worker_data = {
            'name': name,
            'type': worker_type,
            'max_load': max_load,
            'status': 'available'
        }
        
        if host:
            worker_data['host'] = host
        if port:
            worker_data['port'] = port
        if capabilities:
            try:
                worker_data['capabilities'] = json.loads(capabilities)
            except json.JSONDecodeError:
                error_message("Invalid JSON in capabilities")
                return
        if metadata:
            try:
                worker_data['metadata'] = json.loads(metadata)
            except json.JSONDecodeError:
                error_message("Invalid JSON in metadata")
                return
        
        with BitingLipClient(config) as client:
            result = client.register_worker(worker_data)
            success_message(f"Worker '{name}' registered successfully")
            
            if config.verbose:
                click.echo(format_json(result))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to register worker: {str(e)}")


@workers_command.command('update')
@click.argument('worker_id')
@click.option('--status', help='Update worker status')
@click.option('--max-load', type=int, help='Update maximum load')
@click.option('--capabilities', help='Update capabilities as JSON array')
@click.option('--metadata', help='Update metadata as JSON string')
@click.pass_context
def update_worker(ctx, worker_id: str, status: Optional[str], max_load: Optional[int],
                 capabilities: Optional[str], metadata: Optional[str]):
    """Update worker configuration"""
    config = ctx.obj
    
    try:
        worker_data = {}
        
        if status:
            worker_data['status'] = status
        if max_load is not None:
            worker_data['max_load'] = max_load
        if capabilities:
            try:
                worker_data['capabilities'] = json.loads(capabilities)
            except json.JSONDecodeError:
                error_message("Invalid JSON in capabilities")
                return
        if metadata:
            try:
                worker_data['metadata'] = json.loads(metadata)
            except json.JSONDecodeError:
                error_message("Invalid JSON in metadata")
                return
        
        if not worker_data:
            error_message("No updates specified")
            return
        
        with BitingLipClient(config) as client:
            result = client.update_worker(worker_id, worker_data)
            success_message(f"Worker '{worker_id}' updated successfully")
            
            if config.verbose:
                click.echo(format_json(result))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to update worker: {str(e)}")


@workers_command.command('stats')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def worker_stats(ctx, output_format: str):
    """Show worker statistics"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            # Get cluster status which includes worker stats
            response = client.get_cluster_status()
            stats = response.get('worker_stats', {})
            
            if output_format == 'json':
                click.echo(format_json(stats))
            else:
                if not stats:
                    click.echo("No worker statistics available.")
                    return
                
                # Display summary table
                rows = []
                rows.append(['Total Workers', stats.get('total_workers', 0)])
                rows.append(['Active Workers', stats.get('active_workers', 0)])
                rows.append(['Idle Workers', stats.get('idle_workers', 0)])
                rows.append(['Busy Workers', stats.get('busy_workers', 0)])
                rows.append(['Offline Workers', stats.get('offline_workers', 0)])
                rows.append(['Total Load', f"{stats.get('total_load', 0)}/{stats.get('total_capacity', 0)}"])
                
                click.echo(tabulate(rows, headers=['Metric', 'Value'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get worker stats: {str(e)}")


@workers_command.command('health')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def worker_health(ctx, output_format: str):
    """Check worker health status"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            response = client.get_cluster_health()
            health = response.get('workers', {})
            
            if output_format == 'json':
                click.echo(format_json(health))
            else:
                if not health:
                    click.echo("No worker health data available.")
                    return
                
                headers = ['Worker ID', 'Status', 'Health', 'Last Check', 'Issues']
                rows = []
                for worker_id, worker_health in health.items():
                    rows.append([
                        worker_id,
                        worker_health.get('status', 'Unknown'),
                        worker_health.get('health_status', 'Unknown'),
                        worker_health.get('last_health_check', 'N/A'),
                        len(worker_health.get('issues', []))
                    ])
                
                click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get worker health: {str(e)}")

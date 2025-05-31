"""
Task Management Commands

Commands for managing tasks in the BitingLip system.
All operations are routed through the gateway to task-manager.
"""

import click
import json
from typing import Any, Dict, Optional
from tabulate import tabulate
import structlog

from ..client import BitingLipClient, BitingLipAPIError
from ..config import CLIConfig
from ..utils import format_json, handle_api_error, success_message, error_message, format_timestamp

logger = structlog.get_logger(__name__)


@click.group()
@click.pass_context
def tasks_command(ctx):
    """Manage tasks in the BitingLip system"""
    pass


@tasks_command.command('list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.option('--status', help='Filter by task status')
@click.option('--worker', help='Filter by assigned worker')
@click.option('--limit', type=int, default=50, help='Maximum number of tasks to show')
@click.pass_context
def list_tasks(ctx, output_format: str, status: Optional[str], worker: Optional[str], limit: int):
    """List all tasks"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            params: Dict[str, Any] = {'limit': limit}
            if status:
                params['status'] = status
            if worker:
                params['worker'] = worker
                
            response = client.list_tasks(**params)
            tasks = response.get('tasks', [])
            
            if output_format == 'json':
                click.echo(format_json(tasks))
            else:
                if not tasks:
                    click.echo("No tasks found.")
                    return
                
                headers = ['ID', 'Type', 'Status', 'Worker', 'Progress', 'Created', 'Duration']
                rows = []
                for task in tasks:
                    # Calculate duration if task is completed
                    duration = ""
                    if task.get('completed_at') and task.get('created_at'):
                        try:
                            from datetime import datetime
                            created = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
                            completed = datetime.fromisoformat(task['completed_at'].replace('Z', '+00:00'))
                            duration = str(completed - created)
                        except:
                            duration = "N/A"
                    
                    rows.append([
                        task.get('id', 'N/A')[:8] + '...',  # Truncate ID
                        task.get('task_type', 'N/A'),
                        task.get('status', 'N/A'),
                        task.get('assigned_worker', 'Unassigned'),
                        f"{task.get('progress', 0):.1f}%",
                        format_timestamp(task.get('created_at', 'N/A')),
                        duration
                    ])
                
                click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to list tasks: {str(e)}")


@tasks_command.command('show')
@click.argument('task_id')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def show_task(ctx, task_id: str, output_format: str):
    """Show detailed information about a task"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            task = client.get_task(task_id)
            
            if output_format == 'json':
                click.echo(format_json(task))
            else:
                # Display as key-value table
                rows = []
                for key, value in task.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, indent=2)
                    elif key.endswith('_at') and value:
                        value = format_timestamp(value)
                    rows.append([key.replace('_', ' ').title(), str(value)])
                
                click.echo(tabulate(rows, headers=['Property', 'Value'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get task: {str(e)}")


@tasks_command.command('create')
@click.argument('task_type')
@click.option('--model', help='Model to use for the task')
@click.option('--input', 'input_data', help='Input data as JSON string')
@click.option('--priority', type=int, default=1, help='Task priority (1-10)')
@click.option('--metadata', help='Additional metadata as JSON string')
@click.option('--wait', is_flag=True, help='Wait for task completion')
@click.pass_context
def create_task(ctx, task_type: str, model: Optional[str], input_data: Optional[str], 
               priority: int, metadata: Optional[str], wait: bool):
    """Create a new task"""
    config = ctx.obj
    
    try:
        task_data = {
            'task_type': task_type,
            'priority': priority
        }
        
        if model:
            task_data['model_id'] = model
        if input_data:
            try:
                task_data['input_data'] = json.loads(input_data)
            except json.JSONDecodeError:
                error_message("Invalid JSON in input data")
                return
        if metadata:
            try:
                task_data['metadata'] = json.loads(metadata)
            except json.JSONDecodeError:
                error_message("Invalid JSON in metadata")
                return
        
        with BitingLipClient(config) as client:
            result = client.create_task(task_data)
            task_id = result.get('id')
            success_message(f"Task '{task_id}' created successfully")
            
            if wait and task_id:
                click.echo("Waiting for task completion...")
                # Poll task status until completion
                import time
                while True:
                    task_status = client.get_task(task_id)
                    status = task_status.get('status')
                    
                    if status in ['completed', 'failed', 'cancelled']:
                        if status == 'completed':
                            success_message(f"Task completed successfully")
                        elif status == 'failed':
                            error_message(f"Task failed: {task_status.get('error_message', 'Unknown error')}")
                        else:
                            error_message(f"Task was cancelled")
                        break
                    
                    progress = task_status.get('progress', 0)
                    click.echo(f"Progress: {progress:.1f}% - Status: {status}")
                    time.sleep(2)
            
            if config.verbose:
                click.echo(format_json(result))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to create task: {str(e)}")


@tasks_command.command('cancel')
@click.argument('task_id')
@click.option('--force', is_flag=True, help='Force cancellation without confirmation')
@click.pass_context
def cancel_task(ctx, task_id: str, force: bool):
    """Cancel a task"""
    config = ctx.obj
    
    if not force:
        if not click.confirm(f"Are you sure you want to cancel task '{task_id}'?"):
            click.echo("Cancelled.")
            return
    
    try:
        with BitingLipClient(config) as client:
            result = client.cancel_task(task_id)
            success_message(f"Task '{task_id}' cancellation requested")
            
            if config.verbose:
                click.echo(format_json(result))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to cancel task: {str(e)}")


@tasks_command.command('stats')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def task_stats(ctx, output_format: str):
    """Show task statistics"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            # Get overall system status which should include task stats
            response = client.get_system_status()
            stats = response.get('task_stats', {})
            
            if output_format == 'json':
                click.echo(format_json(stats))
            else:
                if not stats:
                    click.echo("No task statistics available.")
                    return
                
                # Display summary table
                rows = []
                rows.append(['Total Tasks', stats.get('total_tasks', 0)])
                rows.append(['Pending Tasks', stats.get('pending_tasks', 0)])
                rows.append(['Running Tasks', stats.get('running_tasks', 0)])
                rows.append(['Completed Tasks', stats.get('completed_tasks', 0)])
                rows.append(['Failed Tasks', stats.get('failed_tasks', 0)])
                rows.append(['Cancelled Tasks', stats.get('cancelled_tasks', 0)])
                rows.append(['Success Rate', f"{stats.get('success_rate', 0):.1f}%"])
                
                click.echo(tabulate(rows, headers=['Metric', 'Value'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get task stats: {str(e)}")


@tasks_command.command('logs')
@click.argument('task_id')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--tail', type=int, default=100, help='Number of lines to show from end')
@click.pass_context
def task_logs(ctx, task_id: str, follow: bool, tail: int):
    """Show task logs"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            # Get task details to check if it exists
            task = client.get_task(task_id)
            
            # For now, just show basic task information
            # In a real implementation, this would fetch actual logs
            click.echo(f"Task ID: {task_id}")
            click.echo(f"Status: {task.get('status', 'Unknown')}")
            click.echo(f"Created: {format_timestamp(task.get('created_at', ''))}")
            
            if task.get('error_message'):
                click.echo(f"Error: {task['error_message']}")
            
            # TODO: Implement actual log fetching from task-manager
            click.echo("\nNote: Full log streaming is not yet implemented.")
            click.echo("Use 'bitinglip tasks show' for detailed task information.")
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get task logs: {str(e)}")

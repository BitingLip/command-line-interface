"""
Model Management Commands

Commands for managing models in the BitingLip system.
All operations are routed through the gateway to model-manager.
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
def models_command(ctx):
    """Manage models in the BitingLip system"""
    pass


@models_command.command('list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.option('--status', help='Filter by model status')
@click.option('--worker', help='Filter by assigned worker')
@click.pass_context
def list_models(ctx, output_format: str, status: Optional[str], worker: Optional[str]):
    """List all models"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            params = {}
            if status:
                params['status'] = status
            if worker:
                params['worker'] = worker
                
            response = client.list_models(**params)
            models = response.get('models', [])
            
            if output_format == 'json':
                click.echo(format_json(models))
            else:
                if not models:
                    click.echo("No models found.")
                    return
                
                headers = ['ID', 'Name', 'Status', 'Worker', 'Created', 'Size']
                rows = []
                for model in models:
                    rows.append([
                        model.get('id', 'N/A'),
                        model.get('name', 'N/A'),
                        model.get('status', 'N/A'),
                        model.get('assigned_worker', 'Unassigned'),
                        model.get('created_at', 'N/A'),
                        model.get('size', 'N/A')
                    ])
                
                click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to list models: {str(e)}")


@models_command.command('show')
@click.argument('model_id')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def show_model(ctx, model_id: str, output_format: str):
    """Show detailed information about a model"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            model = client.get_model(model_id)
            
            if output_format == 'json':
                click.echo(format_json(model))
            else:
                # Display as key-value table
                rows = []
                for key, value in model.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, indent=2)
                    rows.append([key.replace('_', ' ').title(), str(value)])
                
                click.echo(tabulate(rows, headers=['Property', 'Value'], tablefmt='grid'))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to get model: {str(e)}")


@models_command.command('register')
@click.argument('name')
@click.option('--path', help='Model file path')
@click.option('--url', help='Model download URL')
@click.option('--type', 'model_type', help='Model type')
@click.option('--description', help='Model description')
@click.option('--metadata', help='Additional metadata as JSON string')
@click.pass_context
def register_model(ctx, name: str, path: Optional[str], url: Optional[str], 
                   model_type: Optional[str], description: Optional[str], 
                   metadata: Optional[str]):
    """Register a new model"""
    config = ctx.obj
    
    if not path and not url:
        error_message("Either --path or --url must be specified")
        return
    
    try:
        model_data = {
            'name': name,
            'type': model_type or 'unknown',
            'description': description or '',
        }
        
        if path:
            model_data['path'] = path
        if url:
            model_data['url'] = url
        if metadata:
            try:
                model_data['metadata'] = json.loads(metadata)
            except json.JSONDecodeError:
                error_message("Invalid JSON in metadata")
                return
        
        with BitingLipClient(config) as client:
            result = client.create_model(model_data)
            success_message(f"Model '{name}' registered successfully")
            
            if config.verbose:
                click.echo(format_json(result))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to register model: {str(e)}")


@models_command.command('delete')
@click.argument('model_id')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def delete_model(ctx, model_id: str, force: bool):
    """Delete a model"""
    config = ctx.obj
    
    if not force:
        if not click.confirm(f"Are you sure you want to delete model '{model_id}'?"):
            click.echo("Cancelled.")
            return
    
    try:
        with BitingLipClient(config) as client:
            client.delete_model(model_id)
            success_message(f"Model '{model_id}' deleted successfully")
            
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to delete model: {str(e)}")


@models_command.command('download')
@click.argument('model_name')
@click.option('--target-dir', help='Target directory for download')
@click.option('--force', is_flag=True, help='Force re-download if already exists')
@click.pass_context
def download_model(ctx, model_name: str, target_dir: Optional[str], force: bool):
    """Download a model"""
    config = ctx.obj
    
    try:
        params = {}
        if target_dir:
            params['target_dir'] = target_dir
        if force:
            params['force'] = force
            
        with BitingLipClient(config) as client:
            result = client.download_model(model_name, **params)
            success_message(f"Model '{model_name}' download initiated")
            
            if config.verbose:
                click.echo(format_json(result))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to download model: {str(e)}")


@models_command.command('assign')
@click.argument('model_id')
@click.argument('worker_id')
@click.pass_context
def assign_model(ctx, model_id: str, worker_id: str):
    """Assign a model to a worker"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            result = client.assign_model(model_id, worker_id)
            success_message(f"Model '{model_id}' assigned to worker '{worker_id}'")
            
            if config.verbose:
                click.echo(format_json(result))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to assign model: {str(e)}")


@models_command.command('unload')
@click.argument('model_id')
@click.option('--worker', help='Specific worker to unload from (optional)')
@click.pass_context
def unload_model(ctx, model_id: str, worker: Optional[str]):
    """Unload a model from worker(s)"""
    config = ctx.obj
    
    try:
        with BitingLipClient(config) as client:
            result = client.unload_model(model_id, worker_id=worker)
            
            if worker:
                success_message(f"Model '{model_id}' unloaded from worker '{worker}'")
            else:
                success_message(f"Model '{model_id}' unloaded from all workers")
            
            if config.verbose:
                click.echo(format_json(result))
                
    except BitingLipAPIError as e:
        handle_api_error(e)
    except Exception as e:
        error_message(f"Failed to unload model: {str(e)}")

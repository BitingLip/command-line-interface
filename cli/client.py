"""
BitingLip API Client

Gateway-aware API client for communicating with BitingLip services.
Routes all requests through the gateway manager for service discovery and load balancing.
"""

import json
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import structlog

from .config import CLIConfig, get_api_url

logger = structlog.get_logger(__name__)


class BitingLipAPIError(Exception):
    """BitingLip API communication error"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class BitingLipClient:
    """
    Gateway-aware client for BitingLip API services
    
    All requests are routed through the gateway manager which handles:
    - Service discovery
    - Load balancing
    - Authentication
    - Request routing
    """
    
    def __init__(self, config: CLIConfig):
        """
        Initialize API client
        
        Args:
            config: CLI configuration object
        """
        self.config = config
        self.base_url = config.api_url
        self.timeout = config.api_timeout
        
        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=config.api_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'BitingLip-CLI/1.0.0'
        })
        
        # Add authentication if configured
        if config.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {config.api_key}'
            })

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request through the gateway
        
        Args:
            method: HTTP method
            endpoint: API endpoint (will be routed through gateway)
            **kwargs: Additional request parameters
            
        Returns:
            Response data
            
        Raises:
            BitingLipAPIError: On API errors
        """
        url = get_api_url(self.config, endpoint)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            # Log request for debugging
            if self.config.verbose:
                logger.info(
                    "API request made",
                    method=method,
                    url=url,
                    status_code=response.status_code
                )
              # Handle response
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"message": response.text}
            elif response.status_code == 201:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"message": "Created successfully"}
            
            elif response.status_code == 204:
                return {"message": "Success"}
            
            else:
                # Handle error responses
                error_data = None
                try:
                    error_data = response.json()
                    message = error_data.get('detail', f'HTTP {response.status_code}: {response.reason}')
                except json.JSONDecodeError:
                    message = f'HTTP {response.status_code}: {response.reason}'
                
                raise BitingLipAPIError(
                    message=message,
                    status_code=response.status_code,
                    response=error_data
                )
                
        except requests.RequestException as e:
            raise BitingLipAPIError(f"Request failed: {str(e)}")

    # System/Health endpoints
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        return self._make_request('GET', '/api/system/status')
    
    def get_health_check(self) -> Dict[str, Any]:
        """Get system health check"""
        return self._make_request('GET', '/api/health')

    # Model Management endpoints (routed to model-manager)
    def list_models(self, **params) -> Dict[str, Any]:
        """List all models"""
        return self._make_request('GET', '/api/models', params=params)
    
    def get_model(self, model_id: str) -> Dict[str, Any]:
        """Get specific model"""
        return self._make_request('GET', f'/api/models/{model_id}')
    
    def create_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create/register a new model"""
        return self._make_request('POST', '/api/models', json=model_data)
    
    def update_model(self, model_id: str, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update model"""
        return self._make_request('PUT', f'/api/models/{model_id}', json=model_data)
    
    def delete_model(self, model_id: str) -> Dict[str, Any]:
        """Delete model"""
        return self._make_request('DELETE', f'/api/models/{model_id}')

    # Worker Management endpoints (routed to cluster-manager)
    def list_workers(self, **params) -> Dict[str, Any]:
        """List all workers"""
        return self._make_request('GET', '/api/workers', params=params)
    
    def get_worker(self, worker_id: str) -> Dict[str, Any]:
        """Get specific worker"""
        return self._make_request('GET', f'/api/workers/{worker_id}')
    
    def register_worker(self, worker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new worker"""
        return self._make_request('POST', '/api/workers', json=worker_data)
    
    def update_worker(self, worker_id: str, worker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update worker"""
        return self._make_request('PUT', f'/api/workers/{worker_id}', json=worker_data)

    # Task Management endpoints (routed to task-manager)
    def list_tasks(self, **params) -> Dict[str, Any]:
        """List all tasks"""
        return self._make_request('GET', '/api/tasks', params=params)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get specific task"""
        return self._make_request('GET', f'/api/tasks/{task_id}')
    
    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task"""
        return self._make_request('POST', '/api/tasks', json=task_data)
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a task"""
        return self._make_request('POST', f'/api/tasks/{task_id}/cancel')

    # Cluster Management endpoints
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        return self._make_request('GET', '/api/cluster/status')
    
    def get_cluster_health(self) -> Dict[str, Any]:
        """Get cluster health"""
        return self._make_request('GET', '/api/cluster/health')    # Model Operations
    def download_model(self, model_name: str, **params) -> Dict[str, Any]:
        """Download a model"""
        data = {"model_name": model_name, **params}
        return self._make_request('POST', '/api/models/download', json=data)
    
    def assign_model(self, model_id: str, worker_id: str) -> Dict[str, Any]:
        """Assign model to worker"""
        data = {"worker_id": worker_id}
        return self._make_request('POST', f'/api/models/{model_id}/assign', json=data)
    
    def unload_model(self, model_id: str, worker_id: Optional[str] = None) -> Dict[str, Any]:
        """Unload model from worker(s)"""
        data = {"worker_id": worker_id} if worker_id else {}
        return self._make_request('POST', f'/api/models/{model_id}/unload', json=data)

    # Context management for CLI
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

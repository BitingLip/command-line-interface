"""
API Client for Model Management System

Handles HTTP communication with the FastAPI REST API endpoints.
"""

import json
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import structlog

from .config import config, get_api_url


logger = structlog.get_logger(__name__)


class APIError(Exception):
    """API communication error"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ModelManagementClient:
    """Client for Model Management API"""
    
    def __init__(self, cli_config=None, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize API client
        
        Args:
            cli_config: CLI configuration object
            base_url: API base URL (defaults to config)
            timeout: Request timeout (defaults to config)
        """
        self.cli_config = cli_config
        self.base_url = base_url or (cli_config.api_url if cli_config else config.api_url)
        self.timeout = timeout or (cli_config.api_timeout if cli_config else config.api_timeout)
          # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=config.api_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AMD-Cluster-CLI/0.1.0"
        })
        
        # Add authentication if configured
        if config.api_key:
            self.session.headers["Authorization"] = f"Bearer {config.api_key}"
    
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if hasattr(self, 'session'):
            self.session.close()
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            **kwargs: Additional request arguments
            
        Returns:
            Response JSON data
            
        Raises:
            APIError: If request fails
        """
        url = get_api_url(endpoint)
        
        try:
            # Prepare request data
            request_kwargs = {
                "timeout": self.timeout,
                "params": params,
                **kwargs
            }
            
            if data is not None:
                request_kwargs["json"] = data
            
            logger.debug(
                "Making API request",
                method=method,
                url=url,
                params=params,
                has_data=data is not None
            )
            
            # Make request
            response = self.session.request(method, url, **request_kwargs)
              # Handle response
            if response.status_code >= 400:
                error_data = None
                try:
                    error_data = response.json()
                    error_message = error_data.get("message", f"HTTP {response.status_code}")
                except (ValueError, KeyError):
                    error_message = f"HTTP {response.status_code}: {response.text}"
                
                raise APIError(
                    message=error_message,
                    status_code=response.status_code,
                    response=error_data
                )
            
            # Parse JSON response
            try:
                return response.json()
            except ValueError:
                return {"status": "success", "data": response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error("API request failed", error=str(e), url=url)
            raise APIError(f"Request failed: {str(e)}")
      # Health and Status Methods
    
    def health_check(self) -> Dict[str, Any]:
        """Get API health status"""
        return self._make_request("GET", "/api/v1/models/health")
    
    def get_cluster_statistics(self) -> Dict[str, Any]:
        """Get detailed cluster statistics"""
        return self._make_request("GET", "/api/v1/models/cluster/statistics")
    
    def get_component_health(self, component: str) -> Dict[str, Any]:
        """Get health status of a specific component"""
        return self._make_request("GET", f"/api/v1/health/{component}")
    
    def run_diagnostics(self) -> Dict[str, Any]:
        """Run system diagnostics"""
        return self._make_request("POST", "/api/v1/diagnostics")
    
    def get_system_logs(self, lines: int = 100) -> Dict[str, Any]:
        """Get system logs"""
        return self._make_request("GET", "/api/v1/logs", params={"lines": lines})

    # Model Management Methods
    
    def list_models(
        self,
        model_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        List models in registry
        
        Args:
            model_type: Filter by model type
            status: Filter by status
            page: Page number
            page_size: Items per page
              Returns:
            Model list response
        """
        params: Dict[str, Union[str, int]] = {"page": page, "page_size": page_size}
        if model_type:
            params["model_type"] = model_type
        if status:
            params["status"] = status
            
        return self._make_request("GET", "/api/v1/models/", params=params)
    
    def get_model(self, model_name: str) -> Dict[str, Any]:
        """Get specific model information"""
        return self._make_request("GET", f"/api/v1/models/{model_name}")
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific model"""
        return self._make_request("GET", f"/api/v1/models/{model_id}")
    
    def delete_model(self, model_id: str) -> Dict[str, Any]:
        """Delete a model from the system"""
        return self._make_request("DELETE", f"/api/v1/models/{model_id}")
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all models"""
        return self._make_request("GET", "/api/v1/models/status")
    
    def download_model(
        self,
        model_name: str,
        model_type: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Download model from HuggingFace
        
        Args:
            model_name: HuggingFace model name
            model_type: Model type hint
            force: Force re-download
            
        Returns:
            Download response with download_id
        """
        data = {
            "model_name": model_name,
            "force": force
        }
        if model_type:
            data["model_type"] = model_type
            
        return self._make_request("POST", "/api/v1/models/download", data=data)
    
    def get_download_progress(self, download_id: str) -> Dict[str, Any]:
        """Get download progress"""
        return self._make_request("GET", f"/api/v1/models/download/{download_id}/progress")
    
    def assign_model(
        self,
        model_name: str,
        worker_id: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Assign model to worker
        
        Args:
            model_name: Model to assign
            worker_id: Target worker (auto-assign if None)
            force: Force assignment
            
        Returns:
            Assignment response
        """
        data = {
            "model_name": model_name,
            "force": force
        }
        if worker_id:
            data["worker_id"] = worker_id
            
        return self._make_request("POST", "/api/v1/models/assign", data=data)
    
    def unload_model(
        self,
        model_name: str,
        worker_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unload model from worker
        
        Args:
            model_name: Model to unload
            worker_id: Target worker (all workers if None)
            
        Returns:
            Unload response
        """
        data = {"model_name": model_name}
        if worker_id:
            data["worker_id"] = worker_id
            
        return self._make_request("POST", "/api/v1/models/unload", data=data)
    
    def search_huggingface(
        self,
        query: str,
        model_type: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search HuggingFace Hub
        
        Args:
            query: Search query
            model_type: Filter by model type
            limit: Maximum results
            
        Returns:
            Search results
        """
        params = {"query": query, "limit": limit}
        if model_type:
            params["model_type"] = model_type
            
        return self._make_request("GET", "/api/v1/models/search/huggingface", params=params)
      # Worker Management Methods
    
    def list_workers(self) -> List[Dict[str, Any]]:
        """List all workers"""
        response = self._make_request("GET", "/api/v1/models/workers")
        return response.get("workers", [])
    
    def worker_heartbeat(
        self,
        worker_id: str,
        gpu_memory_total: float,
        gpu_memory_used: float,
        models_loaded: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send worker heartbeat
        
        Args:
            worker_id: Worker identifier
            gpu_memory_total: Total GPU memory in GB
            gpu_memory_used: Used GPU memory in GB
            models_loaded: List of loaded models
            
        Returns:
            Heartbeat response
        """
        params = {
            "gpu_memory_total": gpu_memory_total,
            "gpu_memory_used": gpu_memory_used,
            "models_loaded": ",".join(models_loaded or [])
        }
        
        return self._make_request(
            "POST", 
            f"/api/v1/models/workers/{worker_id}/heartbeat",
            params=params        )
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster status"""
        return self._make_request("GET", "/api/v1/cluster/status")
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get detailed cluster information"""
        return self._make_request("GET", "/api/v1/cluster/info")
    
    def restart_cluster(self) -> Dict[str, Any]:
        """Restart the cluster"""
        return self._make_request("POST", "/api/v1/cluster/restart")
    
    def shutdown_cluster(self, timeout: int = 30) -> Dict[str, Any]:
        """Shutdown the cluster gracefully"""
        params = {"timeout": timeout}
        return self._make_request("POST", "/api/v1/cluster/shutdown", params=params)
    
    def get_worker_info(self, worker_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific worker"""
        return self._make_request("GET", f"/api/v1/workers/{worker_id}")
    
    def remove_worker(self, worker_id: str) -> Dict[str, Any]:
        """Remove a worker from the cluster"""
        return self._make_request("DELETE", f"/api/v1/workers/{worker_id}")
    
    def get_workers_status(self) -> Dict[str, Any]:
        """Get status of all workers"""
        return self._make_request("GET", "/api/v1/workers/status")
    
    def ping_worker(self, worker_id: str, timeout: int = 5) -> Dict[str, Any]:
        """Ping a specific worker to check connectivity"""
        return self._make_request("POST", f"/api/v1/workers/{worker_id}/ping", 
                                data={"timeout": timeout})

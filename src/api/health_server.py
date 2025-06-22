"""Health check and metrics server for YouTube Transcriber."""

import asyncio
import json
import os
import psutil
import time
from aiohttp import web
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from prometheus_client import Counter, Histogram, Gauge, generate_latest
import aiohttp_cors

# Metrics
REQUEST_COUNT = Counter('youtube_transcriber_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('youtube_transcriber_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('youtube_transcriber_active_connections', 'Active connections')
MEMORY_USAGE = Gauge('youtube_transcriber_memory_usage_bytes', 'Memory usage in bytes')
CPU_USAGE = Gauge('youtube_transcriber_cpu_usage_percent', 'CPU usage percentage')


class HealthServer:
    """Health check and monitoring server."""
    
    def __init__(self, health_port: int = 8080, metrics_port: int = 9090):
        """Initialize health server.
        
        Args:
            health_port: Port for health check endpoint
            metrics_port: Port for metrics endpoint
        """
        self.health_port = health_port
        self.metrics_port = metrics_port
        self.start_time = datetime.now()
        self.app = web.Application()
        self.metrics_app = web.Application()
        self._setup_routes()
        self._setup_cors()
        
    def _setup_routes(self):
        """Setup HTTP routes."""
        # Health check routes
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/ready', self.readiness_check)
        self.app.router.add_get('/live', self.liveness_check)
        self.app.router.add_get('/info', self.info_endpoint)
        
        # Metrics routes
        self.metrics_app.router.add_get('/metrics', self.metrics_endpoint)
        
    def _setup_cors(self):
        """Setup CORS for the API."""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Basic health check endpoint."""
        REQUEST_COUNT.labels(method='GET', endpoint='/health').inc()
        
        health_status = await self._get_health_status()
        status_code = 200 if health_status['status'] == 'healthy' else 503
        
        return web.json_response(health_status, status=status_code)
    
    async def readiness_check(self, request: web.Request) -> web.Response:
        """Readiness probe for Kubernetes."""
        REQUEST_COUNT.labels(method='GET', endpoint='/ready').inc()
        
        # Check if all dependencies are ready
        checks = await self._perform_readiness_checks()
        all_ready = all(check['ready'] for check in checks.values())
        
        response = {
            'ready': all_ready,
            'checks': checks,
            'timestamp': datetime.now().isoformat()
        }
        
        status_code = 200 if all_ready else 503
        return web.json_response(response, status=status_code)
    
    async def liveness_check(self, request: web.Request) -> web.Response:
        """Liveness probe for Kubernetes."""
        REQUEST_COUNT.labels(method='GET', endpoint='/live').inc()
        
        # Simple liveness check - if we can respond, we're alive
        return web.json_response({
            'alive': True,
            'timestamp': datetime.now().isoformat()
        })
    
    async def info_endpoint(self, request: web.Request) -> web.Response:
        """Application information endpoint."""
        REQUEST_COUNT.labels(method='GET', endpoint='/info').inc()
        
        info = {
            'app_name': os.getenv('APP_NAME', 'YouTube Transcriber'),
            'version': os.getenv('APP_VERSION', '1.0.0'),
            'environment': os.getenv('APP_ENV', 'production'),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'start_time': self.start_time.isoformat(),
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        }
        
        return web.json_response(info)
    
    async def metrics_endpoint(self, request: web.Request) -> web.Response:
        """Prometheus metrics endpoint."""
        # Update system metrics
        self._update_system_metrics()
        
        # Generate Prometheus format metrics
        metrics = generate_latest()
        return web.Response(text=metrics.decode('utf-8'), content_type='text/plain')
    
    async def _get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        try:
            # Check system resources
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Check disk space
            disk = psutil.disk_usage('/')
            
            # Determine health status
            status = 'healthy'
            issues = []
            
            if memory.percent > 90:
                status = 'degraded'
                issues.append(f'High memory usage: {memory.percent}%')
            
            if cpu_percent > 90:
                status = 'degraded'
                issues.append(f'High CPU usage: {cpu_percent}%')
            
            if disk.percent > 90:
                status = 'unhealthy'
                issues.append(f'Low disk space: {disk.percent}% used')
            
            return {
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
                'system': {
                    'memory_percent': memory.percent,
                    'cpu_percent': cpu_percent,
                    'disk_percent': disk.percent
                },
                'issues': issues
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _perform_readiness_checks(self) -> Dict[str, Dict[str, Any]]:
        """Perform readiness checks for all dependencies."""
        checks = {}
        
        # Check YouTube API key
        checks['youtube_api'] = {
            'ready': bool(os.getenv('YOUTUBE_API_KEY')),
            'message': 'API key configured' if os.getenv('YOUTUBE_API_KEY') else 'API key missing'
        }
        
        # Check output directory
        output_dir = Path(os.getenv('OUTPUT_DIRECTORY', '/app/output'))
        checks['output_directory'] = {
            'ready': output_dir.exists() and output_dir.is_dir(),
            'message': f'Output directory {"exists" if output_dir.exists() else "missing"}'
        }
        
        # Check Redis connection (if configured)
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            checks['redis'] = await self._check_redis_connection(redis_url)
        
        # Check disk space
        disk = psutil.disk_usage('/')
        checks['disk_space'] = {
            'ready': disk.percent < 90,
            'message': f'Disk usage: {disk.percent}%'
        }
        
        return checks
    
    async def _check_redis_connection(self, redis_url: str) -> Dict[str, Any]:
        """Check Redis connection."""
        try:
            import aioredis
            redis = await aioredis.from_url(redis_url)
            await redis.ping()
            await redis.close()
            return {'ready': True, 'message': 'Redis connection successful'}
        except Exception as e:
            return {'ready': False, 'message': f'Redis connection failed: {str(e)}'}
    
    def _update_system_metrics(self):
        """Update Prometheus metrics with system information."""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            MEMORY_USAGE.set(memory.used)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            CPU_USAGE.set(cpu_percent)
            
            # Active connections (approximate)
            connections = len(psutil.net_connections())
            ACTIVE_CONNECTIONS.set(connections)
            
        except Exception as e:
            print(f"Error updating metrics: {e}")
    
    async def start(self):
        """Start the health check and metrics servers."""
        # Create runners
        health_runner = web.AppRunner(self.app)
        metrics_runner = web.AppRunner(self.metrics_app)
        
        # Setup runners
        await health_runner.setup()
        await metrics_runner.setup()
        
        # Create sites
        health_site = web.TCPSite(health_runner, '0.0.0.0', self.health_port)
        metrics_site = web.TCPSite(metrics_runner, '0.0.0.0', self.metrics_port)
        
        # Start sites
        await health_site.start()
        await metrics_site.start()
        
        print(f"Health check server started on port {self.health_port}")
        print(f"Metrics server started on port {self.metrics_port}")
        
        # Keep running
        while True:
            await asyncio.sleep(3600)


async def main():
    """Main entry point."""
    health_port = int(os.getenv('HEALTH_CHECK_PORT', '8080'))
    metrics_port = int(os.getenv('METRICS_PORT', '9090'))
    
    server = HealthServer(health_port=health_port, metrics_port=metrics_port)
    await server.start()


if __name__ == '__main__':
    asyncio.run(main())
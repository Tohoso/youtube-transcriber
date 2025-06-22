#!/bin/bash
# YouTube Transcriber Deployment Script
# =====================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NAMESPACE="${NAMESPACE:-youtube-transcriber}"
ENVIRONMENT="${ENVIRONMENT:-production}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-ghcr.io}"
IMAGE_NAME="${IMAGE_NAME:-youtube-transcriber/youtube-transcriber}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check for required tools
    local required_tools=("docker" "kubectl")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed"
            exit 1
        fi
    done
    
    # Check for environment file
    if [[ "$ENVIRONMENT" == "production" && ! -f "$PROJECT_ROOT/.env.production" ]]; then
        log_error ".env.production file not found"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    cd "$PROJECT_ROOT"
    
    docker build \
        -t "${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}" \
        -t "${DOCKER_REGISTRY}/${IMAGE_NAME}:${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
        .
    
    log_success "Docker image built successfully"
}

# Push Docker image
push_image() {
    log_info "Pushing Docker image to registry..."
    
    docker push "${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    docker push "${DOCKER_REGISTRY}/${IMAGE_NAME}:${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
    
    log_success "Docker image pushed successfully"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace "$NAMESPACE" 2>/dev/null || true
    
    # Create secrets from .env file
    if [[ -f "$PROJECT_ROOT/.env.production" ]]; then
        kubectl create secret generic youtube-transcriber-env \
            --from-env-file="$PROJECT_ROOT/.env.production" \
            --namespace="$NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    # Apply Kubernetes manifests
    kubectl apply -f "$PROJECT_ROOT/deployment/k8s/" --namespace="$NAMESPACE"
    
    # Update image
    kubectl set image deployment/youtube-transcriber \
        youtube-transcriber="${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}" \
        --namespace="$NAMESPACE"
    
    # Wait for rollout
    kubectl rollout status deployment/youtube-transcriber --namespace="$NAMESPACE"
    
    log_success "Kubernetes deployment completed"
}

# Deploy with Docker Compose
deploy_docker_compose() {
    log_info "Deploying with Docker Compose..."
    
    cd "$PROJECT_ROOT"
    
    # Stop existing containers
    docker-compose down
    
    # Pull latest images
    docker-compose pull
    
    # Start services
    docker-compose up -d
    
    # Wait for health check
    sleep 10
    
    # Check health
    if curl -f http://localhost:8080/health > /dev/null 2>&1; then
        log_success "Docker Compose deployment completed"
    else
        log_error "Health check failed"
        docker-compose logs --tail=50
        exit 1
    fi
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."
    
    local health_endpoint=""
    
    if [[ "$DEPLOY_TARGET" == "kubernetes" ]]; then
        # Get service endpoint
        health_endpoint=$(kubectl get service youtube-transcriber \
            --namespace="$NAMESPACE" \
            -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):8080
    else
        health_endpoint="localhost:8080"
    fi
    
    # Wait for service to be ready
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f "http://${health_endpoint}/health" > /dev/null 2>&1; then
            log_success "Health check passed"
            break
        fi
        
        attempt=$((attempt + 1))
        log_info "Waiting for service to be ready... (${attempt}/${max_attempts})"
        sleep 5
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        log_error "Health check failed after ${max_attempts} attempts"
        exit 1
    fi
}

# Main deployment flow
main() {
    log_info "Starting YouTube Transcriber deployment..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Deploy Target: ${DEPLOY_TARGET:-docker-compose}"
    
    check_prerequisites
    
    # Build and push image if needed
    if [[ "${BUILD_IMAGE:-true}" == "true" ]]; then
        build_image
        
        if [[ "${PUSH_IMAGE:-false}" == "true" ]]; then
            push_image
        fi
    fi
    
    # Deploy based on target
    if [[ "${DEPLOY_TARGET:-docker-compose}" == "kubernetes" ]]; then
        deploy_kubernetes
    else
        deploy_docker_compose
    fi
    
    # Run health checks
    run_health_checks
    
    log_success "Deployment completed successfully!"
    
    # Show status
    if [[ "${DEPLOY_TARGET:-docker-compose}" == "kubernetes" ]]; then
        kubectl get pods --namespace="$NAMESPACE"
    else
        docker-compose ps
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --tag|-t)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --target)
            DEPLOY_TARGET="$2"
            shift 2
            ;;
        --build)
            BUILD_IMAGE="true"
            shift
            ;;
        --push)
            PUSH_IMAGE="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --environment, -e  Environment (production, staging, development)"
            echo "  --tag, -t         Docker image tag"
            echo "  --target          Deploy target (kubernetes, docker-compose)"
            echo "  --build           Build Docker image"
            echo "  --push            Push Docker image to registry"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main deployment
main
#!/bin/bash

# deploy.sh - Build and deploy Docker image to AWS ECR
# Usage: ./deploy.sh [image-tag]

set -e  # Exit on error

# Configuration - Modify these variables as needed
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="${ECR_REPOSITORY:-rag-pinecone-server}"
IMAGE_TAG="${1:-latest}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi

    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi

    log_info "Prerequisites check passed"
}

# Get or create ECR repository
setup_ecr_repository() {
    log_info "Setting up ECR repository: $ECR_REPOSITORY"

    # Check if repository exists
    if ! aws ecr describe-repositories --repository-names "$ECR_REPOSITORY" --region "$AWS_REGION" &> /dev/null; then
        log_warn "Repository $ECR_REPOSITORY does not exist. Creating..."
        aws ecr create-repository \
            --repository-name "$ECR_REPOSITORY" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256
        log_info "Repository created successfully"
    else
        log_info "Repository already exists"
    fi
}

# Authenticate Docker with ECR
ecr_login() {
    log_info "Authenticating Docker with ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    log_info "Docker authentication successful"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."

    # Get git commit hash for additional tagging (if in git repo)
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

    docker build \
        --platform linux/amd64 \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg GIT_COMMIT="$GIT_COMMIT" \
        -t "$ECR_REPOSITORY:$IMAGE_TAG" \
        -t "$ECR_REPOSITORY:$GIT_COMMIT" \
        .

    log_info "Docker image built successfully"
}

# Tag image for ECR
tag_image() {
    log_info "Tagging image for ECR..."

    ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"

    docker tag "$ECR_REPOSITORY:$IMAGE_TAG" "$ECR_URI:$IMAGE_TAG"

    # Also tag with git commit if available
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "")
    if [ -n "$GIT_COMMIT" ]; then
        docker tag "$ECR_REPOSITORY:$IMAGE_TAG" "$ECR_URI:$GIT_COMMIT"
        log_info "Tagged with commit hash: $GIT_COMMIT"
    fi

    log_info "Image tagged successfully"
}

# Push image to ECR
push_image() {
    log_info "Pushing image to ECR..."

    ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"

    docker push "$ECR_URI:$IMAGE_TAG"

    # Push git commit tag if available
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "")
    if [ -n "$GIT_COMMIT" ]; then
        docker push "$ECR_URI:$GIT_COMMIT"
    fi

    log_info "Image pushed successfully"
}

# Display summary
display_summary() {
    ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

    echo ""
    log_info "==================================================================="
    log_info "Deployment Summary"
    log_info "==================================================================="
    log_info "AWS Account:    $AWS_ACCOUNT_ID"
    log_info "Region:         $AWS_REGION"
    log_info "Repository:     $ECR_REPOSITORY"
    log_info "Image Tag:      $IMAGE_TAG"
    log_info "Git Commit:     $GIT_COMMIT"
    log_info "ECR URI:        $ECR_URI:$IMAGE_TAG"
    log_info "==================================================================="
    echo ""
    log_info "To pull this image:"
    echo "  docker pull $ECR_URI:$IMAGE_TAG"
    echo ""
    log_info "To run this image:"
    echo "  docker run -p 8000:8000 --env-file .env $ECR_URI:$IMAGE_TAG"
    echo ""
}

# Main execution
main() {
    log_info "Starting deployment process..."
    echo ""

    check_prerequisites
    setup_ecr_repository
    ecr_login
    build_image
    tag_image
    push_image
    display_summary

    log_info "Deployment completed successfully!"
}

# Run main function
main

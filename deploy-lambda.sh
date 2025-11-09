#!/bin/bash

################################################################################
# AWS Lambda Deployment Script for RAG Application
#
# This script:
# 1. Builds Docker image for AWS Lambda
# 2. Creates ECR repository (if needed)
# 3. Pushes image to ECR
# 4. Creates/updates Lambda function
# 5. Sets up API Gateway (HTTP API)
# 6. Configures environment variables and permissions
#
# Prerequisites:
# - AWS CLI installed and configured (aws configure)
# - Docker installed and running
# - .env file with your API keys
#
# Usage:
#   ./deploy-lambda.sh [options]
#
# Options:
#   --region REGION        AWS region (default: us-east-1)
#   --function-name NAME   Lambda function name (default: rag-app)
#   --memory MB           Memory size in MB (default: 2048)
#   --timeout SECONDS     Timeout in seconds (default: 300)
#   --help                Show this help message
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="${FUNCTION_NAME:-rag-app}"
ECR_REPO_NAME="${ECR_REPO_NAME:-rag-app}"
MEMORY_SIZE="${MEMORY_SIZE:-2048}"
TIMEOUT="${TIMEOUT:-300}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --function-name)
            FUNCTION_NAME="$2"
            ECR_REPO_NAME="$2"
            shift 2
            ;;
        --memory)
            MEMORY_SIZE="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            grep "^#" "$0" | grep -v "#!/bin/bash" | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to print colored messages
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
log_info "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install it first."
    exit 1
fi

if [ ! -f ".env" ]; then
    log_error ".env file not found. Please create one from .env.example"
    exit 1
fi

# Get AWS account ID
log_info "Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    log_error "Failed to get AWS account ID. Please check your AWS credentials."
    exit 1
fi
log_success "AWS Account ID: $AWS_ACCOUNT_ID"

# ECR repository URI
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"

echo ""
log_info "Deployment Configuration:"
echo "  Region:         $AWS_REGION"
echo "  Function Name:  $FUNCTION_NAME"
echo "  ECR Repository: $ECR_REPO_NAME"
echo "  Memory Size:    ${MEMORY_SIZE} MB"
echo "  Timeout:        ${TIMEOUT} seconds"
echo "  Image URI:      $IMAGE_URI"
echo ""

# Step 1: Create ECR repository if it doesn't exist
log_info "Step 1/7: Checking ECR repository..."
if aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" &> /dev/null; then
    log_success "ECR repository already exists"
else
    log_info "Creating ECR repository: $ECR_REPO_NAME"
    aws ecr create-repository \
        --repository-name "$ECR_REPO_NAME" \
        --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 \
        > /dev/null
    log_success "ECR repository created"
fi

# Step 2: Authenticate Docker to ECR
log_info "Step 2/7: Authenticating Docker to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$ECR_URI" > /dev/null
log_success "Docker authenticated to ECR"

# Step 3: Build Docker image for Lambda
log_info "Step 3/7: Building Docker image for Lambda..."
docker build -f Dockerfile.lambda -t "$ECR_REPO_NAME:$IMAGE_TAG" .
log_success "Docker image built successfully"

# Step 4: Tag image for ECR
log_info "Step 4/7: Tagging image for ECR..."
docker tag "$ECR_REPO_NAME:$IMAGE_TAG" "$IMAGE_URI"
log_success "Image tagged"

# Step 5: Push image to ECR
log_info "Step 5/7: Pushing image to ECR..."
docker push "$IMAGE_URI"
log_success "Image pushed to ECR"

# Step 6: Create or update Lambda function
log_info "Step 6/7: Creating/updating Lambda function..."

# Load environment variables from .env file
ENV_VARS=$(cat .env | grep -v '^#' | grep -v '^$' | awk -F= '{printf "%s=%s,", $1, $2}' | sed 's/,$//')

# Check if Lambda function exists
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" &> /dev/null; then
    log_info "Updating existing Lambda function..."

    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --image-uri "$IMAGE_URI" \
        --region "$AWS_REGION" \
        > /dev/null

    # Wait for update to complete
    log_info "Waiting for function update to complete..."
    aws lambda wait function-updated \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION"

    # Update function configuration
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --memory-size "$MEMORY_SIZE" \
        --timeout "$TIMEOUT" \
        --environment "Variables={$ENV_VARS}" \
        --region "$AWS_REGION" \
        > /dev/null

    log_success "Lambda function updated"
else
    log_info "Creating new Lambda function..."

    # Create execution role if it doesn't exist
    ROLE_NAME="${FUNCTION_NAME}-lambda-role"

    if aws iam get-role --role-name "$ROLE_NAME" &> /dev/null; then
        log_info "Using existing IAM role: $ROLE_NAME"
    else
        log_info "Creating IAM role: $ROLE_NAME"

        # Create trust policy
        cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

        # Create role
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document file:///tmp/trust-policy.json \
            > /dev/null

        # Attach basic execution policy
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

        log_success "IAM role created"

        # Wait for role to be available
        log_info "Waiting for IAM role to propagate..."
        sleep 10
    fi

    ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"

    # Create Lambda function
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --package-type Image \
        --code ImageUri="$IMAGE_URI" \
        --role "$ROLE_ARN" \
        --memory-size "$MEMORY_SIZE" \
        --timeout "$TIMEOUT" \
        --environment "Variables={$ENV_VARS}" \
        --region "$AWS_REGION" \
        > /dev/null

    log_success "Lambda function created"
fi

# Step 7: Create or update API Gateway
log_info "Step 7/7: Setting up API Gateway..."

API_NAME="${FUNCTION_NAME}-api"

# Check if API already exists
API_ID=$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
    --query "Items[?Name=='${API_NAME}'].ApiId" --output text)

if [ -z "$API_ID" ]; then
    log_info "Creating HTTP API Gateway..."

    API_ID=$(aws apigatewayv2 create-api \
        --name "$API_NAME" \
        --protocol-type HTTP \
        --target "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${FUNCTION_NAME}" \
        --region "$AWS_REGION" \
        --query ApiId --output text)

    log_success "API Gateway created: $API_ID"
else
    log_info "API Gateway already exists: $API_ID"
fi

# Add Lambda permission for API Gateway to invoke the function
log_info "Adding Lambda invoke permission for API Gateway..."
aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id "apigateway-invoke-${API_ID}" \
    --action lambda:InvokeFunctionUrl \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*" \
    --region "$AWS_REGION" \
    &> /dev/null || log_warning "Permission may already exist"

# Get API endpoint
API_ENDPOINT=$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
    --query "Items[?ApiId=='${API_ID}'].ApiEndpoint" --output text)

echo ""
echo "================================================================================"
log_success "Deployment completed successfully!"
echo "================================================================================"
echo ""
echo "Lambda Function ARN:"
echo "  arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${FUNCTION_NAME}"
echo ""
echo "API Gateway Endpoint:"
echo "  ${API_ENDPOINT}"
echo ""
echo "Test your API:"
echo "  Health Check:"
echo "    curl ${API_ENDPOINT}/api/health"
echo ""
echo "  Query Endpoint:"
echo "    curl -X POST ${API_ENDPOINT}/api/query \\"
echo "      -H 'Content-Type: application/json' \\"
echo "      -d '{\"query\": \"What is machine learning?\"}'"
echo ""
echo "  API Documentation:"
echo "    ${API_ENDPOINT}/docs"
echo ""
echo "View Lambda logs:"
echo "  aws logs tail /aws/lambda/${FUNCTION_NAME} --follow --region ${AWS_REGION}"
echo ""
echo "================================================================================"

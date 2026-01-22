#!/bin/bash
# Installation script for Weather Proxy Helm Chart

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
NAMESPACE="weather-proxy"
RELEASE_NAME="weather-proxy"
CHART_PATH="./weather-proxy"
ENVIRONMENT="default"
DRY_RUN=false

# Print usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Install Weather Proxy Helm Chart

OPTIONS:
    -n, --namespace NAME       Kubernetes namespace (default: weather-proxy)
    -r, --release NAME         Helm release name (default: weather-proxy)
    -e, --environment ENV      Environment: default, staging, production (default: default)
    -i, --image TAG            Docker image tag to use
    -d, --dry-run              Run in dry-run mode
    -h, --help                 Show this help message

EXAMPLES:
    # Install with default values
    $0

    # Install in production
    $0 --environment production --image 1.0.0

    # Dry run for staging
    $0 --environment staging --dry-run

    # Custom namespace and release
    $0 --namespace my-namespace --release my-release
EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--release)
            RELEASE_NAME="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -i|--image)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Determine values file
case $ENVIRONMENT in
    production)
        VALUES_FILE="values-production.yaml"
        ;;
    staging)
        VALUES_FILE="values-staging.yaml"
        ;;
    default)
        VALUES_FILE="values.yaml"
        ;;
    *)
        echo -e "${RED}Invalid environment: $ENVIRONMENT${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}Weather Proxy Helm Chart Installation${NC}"
echo "=========================================="
echo "Namespace:    $NAMESPACE"
echo "Release:      $RELEASE_NAME"
echo "Environment:  $ENVIRONMENT"
echo "Values File:  $VALUES_FILE"
echo "Chart Path:   $CHART_PATH"
if [ -n "$IMAGE_TAG" ]; then
    echo "Image Tag:    $IMAGE_TAG"
fi
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Mode:         DRY RUN${NC}"
fi
echo "=========================================="
echo

# Check if Helm is installed
if ! command -v helm &> /dev/null; then
    echo -e "${RED}Error: Helm is not installed${NC}"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

# Check if chart directory exists
if [ ! -d "$CHART_PATH" ]; then
    echo -e "${RED}Error: Chart directory not found: $CHART_PATH${NC}"
    exit 1
fi

# Lint the chart
echo -e "${YELLOW}Linting Helm chart...${NC}"
helm lint "$CHART_PATH" -f "$CHART_PATH/$VALUES_FILE"
if [ $? -ne 0 ]; then
    echo -e "${RED}Chart linting failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Chart linting passed${NC}"
echo

# Create namespace if it doesn't exist (not in dry-run)
if [ "$DRY_RUN" = false ]; then
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        echo -e "${YELLOW}Creating namespace: $NAMESPACE${NC}"
        kubectl create namespace "$NAMESPACE"
        echo -e "${GREEN}✓ Namespace created${NC}"
        echo
    fi
fi

# Build Helm install command
HELM_CMD="helm install $RELEASE_NAME $CHART_PATH"
HELM_CMD+=" --namespace $NAMESPACE"
HELM_CMD+=" -f $CHART_PATH/$VALUES_FILE"

if [ -n "$IMAGE_TAG" ]; then
    HELM_CMD+=" --set image.tag=$IMAGE_TAG"
fi

if [ "$DRY_RUN" = true ]; then
    HELM_CMD+=" --dry-run --debug"
fi

# Execute Helm install
echo -e "${YELLOW}Installing Helm chart...${NC}"
echo "Command: $HELM_CMD"
echo

eval $HELM_CMD

if [ $? -eq 0 ]; then
    if [ "$DRY_RUN" = false ]; then
        echo
        echo -e "${GREEN}✓ Weather Proxy successfully installed!${NC}"
        echo
        echo "Next steps:"
        echo "1. Check pod status:"
        echo "   kubectl get pods -n $NAMESPACE"
        echo
        echo "2. Watch deployment:"
        echo "   kubectl rollout status deployment/$RELEASE_NAME -n $NAMESPACE"
        echo
        echo "3. Port-forward to access locally:"
        echo "   kubectl port-forward svc/$RELEASE_NAME 8080:80 -n $NAMESPACE"
        echo
        echo "4. Test the service:"
        echo "   curl http://localhost:8080/health"
        echo "   curl 'http://localhost:8080/weather?city=London'"
        echo
    else
        echo
        echo -e "${GREEN}✓ Dry run completed successfully${NC}"
    fi
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi

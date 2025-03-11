#!/bin/zsh

# Function to activate the production environment
activate_production() {
    echo "Activating production environment..."
    source .venv/bin/activate
    echo "Production environment activated."
}

# Function to activate the development environment
activate_development() {
    echo "Activating development environment..."
    source .venv-dev/bin/activate
    echo "Development environment activated."
}

# Function to install dependencies
install_dependencies() {
    if [[ "$1" == "production" ]]; then
        activate_production
        echo "Installing production dependencies..."
        pip install -r requirements.txt
    elif [[ "$1" == "development" ]]; then
        activate_development
        echo "Installing development dependencies..."
        pip install -r requirements-dev.txt
    else
        echo "Invalid environment specified. Use 'production' or 'development'."
    fi
    deactivate
}

# Function to deploy the function app
deploy_function_app() {
    activate_production
    echo "Deploying function app..."
    # Add your deployment commands here, e.g., using Azure CLI
    # az functionapp deployment source config-zip --resource-group <resource-group> --name <function-app-name> --src <zip-file>
    deactivate
    echo "Function app deployed."
}

# Main script logic
case "$1" in
    "activate-prod")
        activate_production
        ;;
    "activate-dev")
        activate_development
        ;;
    "install-prod")
        install_dependencies "production"
        ;;
    "install-dev")
        install_dependencies "development"
        ;;
    "deploy")
        deploy_function_app
        ;;
    *)
        echo "Usage: $0 {activate-prod|activate-dev|install-prod|install-dev|deploy}"
        ;;
esac
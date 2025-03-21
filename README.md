# RSS Analyzer Poster

## Project Overview

The RSS Analyzer Poster project is designed to analyze RSS feeds, summarize their content, and provide engagement scores. This project leverages Azure Functions for serverless execution and Terraform for infrastructure management.

### Key Components

- **RssIngestionService**: Responsible for processing and analyzing RSS feeds, enriching them with AI, and storing the results in Azure Table Storage.
- **Azure Functions**: Serverless execution of the RSS feed processing.
- **Terraform**: Infrastructure management.
- **GitHub Actions**: CI/CD pipeline for automated testing and deployment.

## Repository Structure

```text
rss-analyzer-poster/
├── .github/
│   └── workflows/
│       ├── terraform.yml
│       ├── ci_pipeline.yml
│       └── cd_pipeline.yml
├── infra/
│   ├── appserviceplan.tf
│   ├── entra.tf
│   ├── keyvault.tf
│   ├── main.tf
│   ├── openai.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── storageaccounts.tf
│   └── variables.tf
├── samples/
│   ├── rss_feed_engagement_sample.csv
│   └── rss_feed_engagement_with_content.csv
├── utils/
│   ├── helper.py
│   └── parser.py
├── .funcignore
├── .gitignore
├── README.md
├── azure_clients.py
├── function_app.py
├── host.json
├── requirements.txt
└── rss_ingestion_service.py
```

## Key Files and Directories

- **function_app.py**: Main entry point for the Azure Function App.
- **rss_ingestion_service.py**: Contains the logic for processing RSS feeds.
- **infra/**: Contains Terraform configuration files for provisioning Azure resources.
- **samples/**: Contains sample data for testing and documentation.
- **utils/**: Contains utility modules for the application.
- **.github/workflows/**: Contains GitHub Actions workflows for CI/CD.

## Sample Data

The `samples` directory contains CSV files with sample RSS feed data:

- **rss_feed_engagement_with_content.csv**: Contains RSS feed data with full content.
- **rss_feed_engagement_sample.csv**: Contains RSS feed data with summarized content.

## Infrastructure

The `infra` directory contains Terraform configuration files for provisioning the necessary Azure resources:

- **main.tf**: Establishes core infrastructure components.
- **keyvault.tf**: Manages secure storage of sensitive information.
- **appserviceplan.tf**: Configures the hosting environment for the function app.
- **entra.tf**: Handles Azure Active Directory (AAD) integration.
- **providers.tf**: Specifies the necessary providers for resource management.
- **storageaccounts.tf**: Configures storage solutions for the application.
- **outputs.tf**: Provides essential information about the deployed resources.
- **variables.tf**: Defines variables used in the Terraform configuration.
- **versions.tf**: Specifies the required Terraform version and provider versions.

## GitHub Actions

The `.github/workflows` directory contains the CI/CD pipeline configuration:

- **terraform.yml**: Automates the execution of Terraform commands (plan, apply, destroy).
- **ci_pipeline.yml**: Defines the CI pipeline for building, testing, and uploading build artifacts.
- **cd_pipeline.yml**: Defines the CD pipeline for deploying the application to Azure.

## Usage

1. **Set up the virtual environment**:

    ```sh
    python -m venv venv
    source venv/bin/activate
    ```

2. **Install dependencies**:

    ```sh
    pip install -r requirements.txt
    ```

3. **Run the application**:

    ```sh
    func start
    ```

4. **Deploy the application**:
    The deployment is handled by the GitHub Actions workflow defined in `.github/workflows/main.yml`.

## License

This project is licensed under the MIT License.

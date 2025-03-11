# RSS Analyzer Poster

## Project Overview

The RSS Analyzer Poster project is designed to analyze RSS feeds, summarize their content, and provide engagement scores. This project leverages Azure Functions for serverless execution and Terraform for infrastructure management.

## Repository Structure

```text
rss-analyzer-poster/
├── .github/
│   └── workflows/
│       └── main_rssanalyzerposterrssai01.yml
├── .vscode/
│   ├── extensions.json
│   └── launch.json
├── infra/
│   ├── main.tf
│   ├── keyvault.tf
│   ├── appserviceplan.tf
│   ├── entra.tf
│   ├── providers.tf
│   ├── storageaccounts.tf
│   └── outputs.tf
├── samples/
│   ├── rss_feed_engagement_with_content.csv
│   └── rss_feed_engagement_sample.csv
├── function_app.py
├── rss_processor.py
├── requirements.txt
├── requirements-dev.txt
├── host.json
├── local.settings.json
├── .gitignore
└── README.md
```

## Key Files and Directories

- **function_app.py**: Main entry point for the Azure Function App.
- **rss_processor.py**: Contains the logic for processing RSS feeds.
- **infra/**: Contains Terraform configuration files for provisioning Azure resources.
- **samples/**: Contains sample data and markdown files for testing and documentation.
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

## GitHub Actions

The `.github/workflows` directory contains the CI/CD pipeline configuration:

- **main_rssanalyzerposterrssai01.yml**: Defines the workflow for building, testing, and deploying the Azure Function App.

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
    The deployment is handled by the GitHub Actions workflow defined in `.github/workflows/main_rssanalyzerposterrssai01.yml`.

## License

This project is licensed under the MIT License.

# RSS Analyzer Poster

## Project Overview

The RSS Analyzer Poster project is designed to analyze RSS feeds, summarize their content, and provide engagement scores. This project leverages Azure Functions for serverless execution and Terraform for infrastructure management.

### Key Components

- **RssIngestionService**: Responsible for processing and analyzing RSS feeds and storing the results in Azure Table Storage.
- **AIEnrichmentService**: Provides AI-driven enrichment for RSS feed data, including sentiment analysis, readability scoring, and embedding generation.
- **Feed**: Represents an RSS feed with metadata such as title, link, language, and publisher. Supports operations like creation, update, and deletion in Azure Table Storage.
- **Entry**: Represents an RSS feed entry, including properties like title, link, content, and tags. Supports persistence in Azure Table Storage and content caching in Azure Blob Storage.
- **AIEnrichment**: Represents AI-generated enhancements for RSS entries, including summaries, readability scores, engagement metrics, and embeddings. Supports persistence in Azure Table Storage and Azure Blob Storage.
- **Post**: Represents a blog post with attributes like title, content, and draft status.
- **Azure Functions**: Serverless execution of the RSS feed processing.
- **Terraform**: Infrastructure management.
- **GitHub Actions**: CI/CD pipeline for automated testing and deployment.

## Repository Structure

```text
.
├── .codetocloud
│   └── azure.json
├── .funcignore
├── .github
│   ├── copilot-instructions.md
│   └── workflows
│       ├── cd_pipeline.yml
│       ├── ci_pipeline.yml
│       └── terraform.yml
├── .gitignore
├── .vscode
│   ├── extensions.json
│   ├── launch.json
│   ├── settings.json
│   └── tasks.json
├── README.md
├── entities
│   ├── entry.py
│   ├── feed.py
│   └── post.py
├── examples
│   ├── config.json
│   ├── rss_feed_engagement_sample.csv
│   ├── rss_feed_engagement_with_content.csv
│   ├── sample_list_schema.json
│   ├── system.md
│   └── user.md
├── function_app.py
├── host.json
├── infra
│   ├── README.md
│   ├── appserviceplan.tf
│   ├── entra.tf
│   ├── keyvault.tf
│   ├── main.tf
│   ├── openai.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── servicebus.tf
│   ├── storageaccount.tf
│   └── variables.tf
├── requirements.txt
├── services
│   ├── ai_enrichment.py
│   └── rss.py
├── tests
│   ├── conftest.py
│   ├── test_ai_enrichment.py
│   ├── test_decorators.py
│   └── test_entry.py
└── utils
    ├── azclients.py
    ├── config.py
    ├── context.py
    ├── decorators.py
    ├── helper.py
    ├── logger.py
    ├── parser.py
    └── rss_lists.py
```

## Key Files and Directories

- **function_app.py**: Main entry point for the Azure Function App.
- **rss_ingestion_service.py**: Contains the logic for processing RSS feeds.
- **azure_clients.py**: Provides Azure-specific client utilities for interacting with Azure services.
- **infra/**: Contains Terraform configuration files for provisioning Azure resources.
- **samples/**: Contains sample data for testing and documentation.
- **utils/**: Contains utility modules for the application.
- **examples/**: Contains example system and user messages for testing summarization and scoring.
- **.github/workflows/**: Contains GitHub Actions workflows for CI/CD.

## Sample Data

The `examples` directory contains sample data and schemas for testing and documentation:

- **config.json**: Configuration file for RSS feed processing.
- **sample_list_schema.json**: Schema for validating RSS feed lists.
- **system.md**: Example system messages for testing summarization and scoring.
- **user.md**: Example user messages for testing summarization and scoring.

## Infrastructure

The `infra` directory contains Terraform configuration files for provisioning the necessary Azure resources:

- **main.tf**: Establishes core infrastructure components, including resource groups and dependencies.
- **keyvault.tf**: Configures Azure Key Vault for secure storage of sensitive information, such as secrets and keys.
- **appserviceplan.tf**: Defines the hosting environment for the Azure Function App using a Linux-based service plan.
- **entra.tf**: Manages Azure Active Directory (AAD) integration, including application registration and access policies.
- **providers.tf**: Specifies the required Terraform providers for managing Azure resources.
- **storageaccount.tf**: Configures Azure Storage Accounts, including blob containers and table storage for RSS feed data.
- **servicebus.tf**: Sets up Azure Service Bus for managing message queues, such as RSS feed updates and AI enrichment tasks.
- **openai.tf**: Configures Azure OpenAI resources for AI-driven enrichment tasks.
- **outputs.tf**: Defines outputs for key resource information, such as connection strings and endpoints.
- **variables.tf**: Declares variables used across the Terraform configuration files for better reusability and customization.

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

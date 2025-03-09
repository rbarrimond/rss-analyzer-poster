# RSS Analyzer Poster Infrastructure

This repository contains Terraform Infrastructure as Code (IaC) for deploying and managing the infrastructure required for the RSS Analyzer Poster project on Azure.

## Contents

- **main.tf**: Establishes the core infrastructure components.
  - **Resource Group**: Organizes all related resources within a specific Azure location.
  - **Application Insights**: Provides monitoring and diagnostic capabilities for the application.
  - **Linux Function App**: Hosts the RSS Analyzer Poster application, enabling serverless execution.

- **keyvault.tf**: Manages secure storage of sensitive information.
  - **Key Vault**: Stores secrets and keys securely, with defined access policies for authorized applications.

- **appserviceplan.tf**: Configures the hosting environment for the function app.
  - **Service Plan**: Allocates resources for running the function app, using a cost-effective Linux-based plan.

- **entra.tf**: Handles Azure Active Directory (AAD) integration.
  - **AAD Application**: Manages identity and access for the RSS Feed Analyzer application.
  - **AAD Application Password**: Secures the application with a password, ensuring controlled access.

- **providers.tf**: Specifies the necessary providers for resource management.
  - **AzureRM Provider**: Facilitates interaction with Azure resources.
  - **AzAPI Provider**: Enables access to Azure APIs for advanced configurations.
  - **AzureAD Provider**: Manages Azure Active Directory resources and identities.

- **storageaccounts.tf**: Configures storage solutions for the application.
  - **General-Purpose Storage Account**: Provides scalable storage for application data.
  - **Blob Container**: Configures a container within the storage account specifically for storing configuration files and other necessary data for the function app.
  - **Deployment Storage Account**: Dedicated storage for deployment artifacts, ensuring efficient application updates.

- **outputs.tf**: Provides essential information about the deployed resources.
  - **Storage Account Blob Endpoint**: Outputs the primary blob endpoint, which is the access point for the blob container storing application data and configurations.
  - **Storage Account Table Endpoint**: Outputs the primary table endpoint for structured data storage.
  - **Storage Account Queue Endpoint**: Outputs the primary queue endpoint for message queuing.
  - **Storage Account File Endpoint**: Outputs the primary file endpoint for file storage.
  - **Function App Name**: Outputs the name of the RSS Analyzer Poster Function App.
  - **Function App Default Hostname**: Outputs the default hostname for accessing the function app.
  - **Function App URL**: Outputs the URL for direct access to the function app.

## Purpose

The Terraform configuration in this repository automates the provisioning and management of Azure resources needed for the RSS Analyzer Poster project. It ensures consistency and efficiency in deploying the infrastructure.

## Results

Running this Terraform configuration will provision the following Azure resources:

- A resource group to organize all related resources.
- An Azure Key Vault for secure storage of secrets and keys.
- Application Insights for monitoring and logging.
- An Azure App Service Plan for hosting function apps.
- A Linux-based Azure Function App for the project.
- Storage accounts for general-purpose use and function deployment.
- Configured blob containers for storing configuration files.
- System-assigned managed identities and Key Vault references.

This setup provides a scalable and secure environment for the RSS Analyzer Poster project, enabling efficient deployment and management of resources on Azure.

# RSS Analyzer Poster Infrastructure

This repository contains Terraform Infrastructure as Code (IaC) for deploying and managing the infrastructure required for the RSS Analyzer Poster project on Azure.

## Contents

- **keyvault.tf**: Configures an Azure Key Vault to securely store secrets and keys. It includes access policies for the function app to retrieve and list secrets.
- **outputs.tf**: Defines outputs for various Azure resources, such as storage account endpoints, Cosmos DB endpoints, and function app IDs, which can be referenced in other configurations or scripts.
- **main.tf**: Sets up the Azure client configuration, resource group, Application Insights for monitoring, and a Linux-based Azure Function App for the RSS Analyzer Poster project.
- **appserviceplan.tf**: Configures an Azure App Service Plan with a Basic (B1) SKU for hosting the Azure Function Apps.
- **providers.tf**: Specifies the required providers (azurerm and azapi) and configures the Azure provider with the subscription ID.
- **storageaccount.tf**: Defines configurations for Azure Storage Accounts, including a general-purpose storage account, a blob container for function app configurations, and a dedicated storage account for function app deployment artifacts.
- **variables.tf**: Declares variables for subscription ID, resource suffix, location, tenant ID, and client ID.

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

This setup provides a scalable and secure environment for the RSS Analyzer Poster project, enabling efficient deployment and management of resources on Azure.

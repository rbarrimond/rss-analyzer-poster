# =================================================================================================
# RSS Analyzer Poster Infrastructure Configuration
# =================================================================================================
# 
# Project: RSS Analyzer Poster
# Description:
# This Terraform configuration file defines the necessary Azure infrastructure to support the 
# RSS Analyzer Poster application. The application is designed to fetch, analyze, and curate 
# RSS feed content using AI-driven insights, then automate content posting to platforms like 
# LinkedIn, Substack, and WordPress.
#
# Purpose:
# - Automate the provisioning and management of Azure resources for the RSS Analyzer Poster.
# - Ensure scalability, security, and cost-effectiveness by leveraging managed cloud services.
# - Enable AI-powered content processing through seamless integration with Azure OpenAI and 
#   Microsoft Graph API.
# - Implement best practices in infrastructure as code (IaC), promoting consistency, 
#   version control, and repeatability across environments.
#
# Infrastructure Components:
# - Resource Group: A logical container for all Azure resources related to the project.
# - Application Insights: Provides monitoring and observability for performance and health.
# - Linux Function App: Hosts the serverless application that processes RSS feeds.
# - Storage Account: Stores processed data, AI-generated insights, and metadata.
# - Role Assignments: Grants necessary permissions for AI services and Azure resources.
#
# Key Features:
# - Scalability: Serverless compute with Azure Functions to optimize costs.
# - Security: Uses Azure Key Vault for securing sensitive configurations.
# - Observability: Integrated health checks and monitoring with Application Insights.
# - Automation: AI-driven workflows for intelligent content curation and posting.
#
# Usage:
# - Deploy using Terraform to provision and manage infrastructure efficiently.
# - Modify variable inputs (variables.tf) to customize deployment based on environment needs.
# - Follow the README.md documentation for setup, configuration, and maintenance.
# =================================================================================================

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "rg" {
  name     = "rg${var.resource_suffix}"
  location = var.location
  tags = {
    azd-env-name = var.resource_suffix
  }
}

resource "azurerm_application_insights" "app_insights" {
  name                = "appInsights${var.resource_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
}

resource "azurerm_linux_function_app" "rss_analyzer_poster" {
  name                = "rssAnalyzerPoster${var.resource_suffix}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  storage_account_name       = azurerm_storage_account.strg_funcdep.name
  storage_account_access_key = azurerm_storage_account.strg_funcdep.primary_access_key
  service_plan_id            = azurerm_service_plan.funcplanlinux.id

  site_config {
    always_on = true

    # Health check configuration
    health_check_path                 = "/health" # Endpoint for health checks
    health_check_eviction_time_in_min = 10        # Time in minutes to evict unhealthy instances

    application_insights_connection_string = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.app_insights_connection_string.versionless_id})"
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    "AZURE_STORAGEACCOUNT_BLOBENDPOINT"  = azurerm_storage_account.strg_storageaccount.primary_blob_endpoint
    "AZURE_STORAGEACCOUNT_TABLEENDPOINT" = azurerm_storage_account.strg_storageaccount.primary_table_endpoint
    "AZURE_STORAGEACCOUNT_QUEUEENDPOINT" = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
    "AZURE_STORAGEACCOUNT_FILEENDPOINT"  = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
    "RSSAP_TENANT_ID"                    = var.tenant_id
    "RSSAP_CLIENT_ID"                    = azuread_application.rss_feed_analyzer.client_id
    "RSSAP_CLIENT_SECRET"                = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.rssap_client_secret.versionless_id})"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    azd-env-name = var.resource_suffix
  }

  lifecycle {
    ignore_changes = [
      # Oryx build from VS Code
      app_settings["WEBSITE_RUN_FROM_PACKAGE"],
      app_settings["BUILD_FLAGS"],
      app_settings["ENABLE_ORYX_BUILD"],
      app_settings["SCM_DO_BUILD_DURING_DEPLOYMENT"],
      app_settings["XDG_CACHE_HOME"],
    ]
  }
}

resource "azurerm_role_assignment" "cognitive_account_access" {
  principal_id         = azurerm_linux_function_app.rss_analyzer_poster.identity[0].principal_id
  role_definition_name = "Cognitive Services OpenAI User"
  scope                = data.azurerm_cognitive_account.main.id
}

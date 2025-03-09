# ===================================================================
# Azure Client Configuration
# Retrieves the current Azure client configuration for use in
# resource management and deployment.
# ===================================================================
data "azurerm_client_config" "current" {}

# ===================================================================
# Azure Resource Group
# Creates a resource group to contain all related Azure resources
# for the RSS Analyzer Poster project.
# ===================================================================
resource "azurerm_resource_group" "rg" {
  name     = "rg${var.resource_suffix}"
  location = var.location
  tags = {
    azd-env-name = var.resource_suffix
  }
}

# ===================================================================
# Azure Application Insights
# Configures Application Insights for monitoring and logging of
# Azure Functions and other resources. This provides insights into
# application performance and usage.
# ===================================================================
resource "azurerm_application_insights" "app_insights" {
  name                = "appInsights${var.resource_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
}

# ===================================================================
# Azure Linux Function App: RSS Analyzer Poster
# Deploys a Linux-based Azure Function App for the RSS Analyzer
# Poster project. Configures storage, service plan, and health checks.
# ===================================================================
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
    health_check_path = "/health"  # Endpoint for health checks
    health_check_eviction_time_in_min = 10  # Time in minutes to evict unhealthy instances
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"              = "python"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.app_insights_connection_string.id})"
    "AZURE_STORAGEACCOUNT_BLOBENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_blob_endpoint
    "AZURE_STORAGEACCOUNT_TABLEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_table_endpoint
    "AZURE_STORAGEACCOUNT_QUEUEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
    "AZURE_STORAGEACCOUNT_FILEENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
    "WEBSITE_RUN_FROM_PACKAGE"              = "1"  # Enable running from package
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    azd-env-name = var.resource_suffix
  }
}

# Resource to manually set the runtime version for the Function App
resource "azapi_resource" "fix_linux_fx_version" {
  type      = "Microsoft.Web/sites@2022-09-01"  # Ensure correct API version
  name      = azurerm_linux_function_app.rss_analyzer_poster.name
  location  = azurerm_linux_function_app.rss_analyzer_poster.location
  parent_id = azurerm_resource_group.rg.id

  body = jsonencode({
    properties = {
            siteConfig = {
        linuxFxVersion = "PYTHON|3.11"  # Ensure the casing is correct
      }
    }
  })

  # Ensure this resource is applied after the Function App is created
  depends_on = [
    azurerm_linux_function_app.rss_analyzer_poster
  ]
}

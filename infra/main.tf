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

resource "azurerm_key_vault_secret" "app_insights_connection_string" {
  name         = "AppInsightsConnectionString"
  value        = azurerm_application_insights.app_insights.connection_string
  key_vault_id = azurerm_key_vault.kv.id
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

  # Explicitly define dependencies
  depends_on = [
    azurerm_service_plan.funcplanlinux,
    azurerm_key_vault.kv,  # Ensure the Key Vault is created before the Function App
    azurerm_key_vault_secret.app_insights_connection_string  # Ensure the secret is created before the Function App
  ]
}

# Use azapi_resource to manually set the runtime version
resource "azapi_resource" "fix_linux_fx_version" {
  type      = "Microsoft.Web/sites@2022-09-01"  # Ensure correct API version
  name      = azurerm_linux_function_app.rss_analyzer_poster.name
  location  = azurerm_linux_function_app.rss_analyzer_poster.location
  parent_id = azurerm_resource_group.rg.id

  body = jsonencode({
    properties = {
      siteConfig = {
        linuxFxVersion = "Python|3.11"  # Replace with your required runtime
      }
    }
  })

  # Ensure this resource is applied after the Function App is created
  depends_on = [
    azurerm_linux_function_app.rss_analyzer_poster
  ]
}
data "azapi_resource" "function_app_identity" {
  type      = "Microsoft.Web/sites@2022-09-01"
  name      = azurerm_linux_function_app.rss_analyzer_poster.name
  parent_id = azurerm_resource_group.rg.id

  response_export_values = ["identity"]
}

resource "azurerm_key_vault_access_policy" "function_app_policy" {
  key_vault_id = azurerm_key_vault.kv.id

  tenant_id = var.tenant_id
  object_id = jsondecode(data.azapi_resource.function_app_identity.output).identity.principalId

  secret_permissions = ["Get", "List"]  # Correctly capitalized permissions
}

resource "azurerm_key_vault_access_policy" "admin_policy" {
  key_vault_id = azurerm_key_vault.kv.id

  tenant_id = var.tenant_id
  object_id = var.admin_object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]  # Correctly capitalized permissions
}


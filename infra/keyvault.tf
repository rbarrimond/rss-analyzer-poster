################################################################################
# Azure Key Vault Configuration
#
# An Azure Key Vault is a cloud service for securely storing and accessing 
# secrets, keys, and certificates. It provides a centralized and secure 
# solution for managing sensitive information, ensuring data protection 
# and compliance.
#
# Purpose in Infrastructure:
# - Securely stores secrets and keys used by applications and services.
# - Provides centralized access control and auditing capabilities.
# - Supports integration with Azure Active Directory for authentication.
#
# In this configuration, the Key Vault is set up with a standard SKU and 
# is deployed in the same location as the existing resource group. Purge 
# protection is disabled to allow immediate deletion if needed.
################################################################################

resource "azurerm_key_vault" "kv" {
  name                = "keyVault${var.resource_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  purge_protection_enabled = false

  # Enable private access settings for the storage account
  public_network_access_enabled = true
  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices" # Allow access from Azure services, including the Azure Portal and Azure CLI
  }

  tags = {
    azd-env-name = var.resource_suffix
  }
}

# Key Vault access policy for the Function App's system-assigned managed identity
resource "azurerm_key_vault_access_policy" "function_app_policy" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = var.tenant_id
  object_id    = azurerm_linux_function_app.rss_analyzer_poster.identity[0].principal_id

  secret_permissions = ["Get", "List"]
}

# Key Vault access policy for the administrator
resource "azurerm_key_vault_access_policy" "admin_policy" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = var.tenant_id
  object_id    = var.admin_object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge", "Backup", "Restore", "Recover"]
}

# Store sensitive application credentials in Azure Key Vault
resource "azurerm_key_vault_secret" "app_insights_connection_string" {
  name         = "AppInsightsConnectionString"
  value        = azurerm_application_insights.app_insights.connection_string
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "rssap_tenant_id" {
  name         = "RssapTenantId"
  value        = var.tenant_id
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "rssap_client_id" {
  name         = "RssapClientId"
  value        = azuread_application.rss_feed_analyzer.client_id
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "rssap_client_secret" {
  name         = "RssapClientSecret"
  value        = azuread_application_password.rss_feed_secret.value
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "azure_openai_api_key" {
  name         = "AzureOpenAIAPIKey"
  value        = var.azure_openai_api_key
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "azure_openai_model" {
  name         = "AzureOpenAIModel"
  value        = var.azure_openai_model
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "azure_openai_deployment" {
  name         = "AzureOpenAIDeployment"
  value        = var.azure_openai_deployment
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "azure_openai_endpoint" {
  name         = "AzureOpenAIEndpoint"
  value        = var.azure_openai_endpoint
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "openai_api_version" {
  name         = "OpenAIApiVersion"
  value        = var.openai_api_version
  key_vault_id = azurerm_key_vault.kv.id
}

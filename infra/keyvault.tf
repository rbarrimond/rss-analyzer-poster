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

  tags = {
    azd-env-name = var.resource_suffix
  }
}

# Azure AD service principal for the Function App
data "azuread_service_principal" "function_app_sp" {
  client_id = azuread_application.rss_feed_analyzer.client_id
}

# Key Vault access policy for the Function App
resource "azurerm_key_vault_access_policy" "function_app_policy" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = var.tenant_id
  object_id    = data.azuread_service_principal.function_app_sp.object_id
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
# This includes AppInsights connection string, Tenant ID, Client ID, and Client Secret
# for secure access management.
resource "azurerm_key_vault_secret" "app_insights_connection_string" {
  name         = "AppInsightsConnectionString"
  value        = azurerm_application_insights.app_insights.connection_string
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [
    azurerm_key_vault_access_policy.function_app_policy,
    azurerm_key_vault_access_policy.admin_policy
  ]
}

resource "azurerm_key_vault_secret" "rsapp_tenant_id" {
  name         = "RssapTenantId"
  value        = var.tenant_id
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [
    azurerm_key_vault_access_policy.function_app_policy,
    azurerm_key_vault_access_policy.admin_policy
  ]
}

resource "azurerm_key_vault_secret" "rssap_client_id" {
  name         = "RssapClientId"
  value        = azuread_application.rss_feed_analyzer.client_id
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [
    azurerm_key_vault_access_policy.function_app_policy,
    azurerm_key_vault_access_policy.admin_policy
  ]
}

resource "azurerm_key_vault_secret" "rssap_client_secret" {
  name         = "RssapClientSecret"
  value        = azuread_application_password.rss_feed_secret.value
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [
    azurerm_key_vault_access_policy.function_app_policy,
    azurerm_key_vault_access_policy.admin_policy
  ]
}

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

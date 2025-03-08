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

  # Access policy for the function app
  # This block grants the function app access to the Key Vault, allowing it to retrieve
  # and list secrets necessary for its operation. The access is controlled using Azure AD
  # tenant and object IDs, ensuring secure and managed access.
  access_policy {
    tenant_id = var.tenant_id
    object_id = var.object_id  # Updated to use object_id

    secret_permissions = [
      "Get",
      "List"
    ]
  }
}

# ===================================================================
# Azure Storage Account Configuration
#
# This file defines the configuration for Azure Storage Accounts used
# in the RSS Analyzer Poster project. It includes:
# - A general-purpose storage account for application data and logs.
# - A blob container for storing function app configuration files.
# - A dedicated storage account for function app deployment artifacts.
# ===================================================================

# Create an Azure Storage Account
# This storage account is intended for general-purpose use, supporting
# various storage types such as Blob, File, Queue, and Table storage.
# It is configured with Local Redundant Storage (LRS) for cost efficiency
# and ensures data security with private access settings.

resource "azurerm_storage_account" "strg_storageaccount" {
  name                          = "storage${var.resource_suffix}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = true

  tags = { 
    azd-env-name = var.resource_suffix 
  }
}

# Create a Blob Container for Function App Configurations
# This container is used to store configuration files required by the function app.
# It is stored in the general-purpose storage account.

resource "azurerm_storage_container" "config_container" {
  name                  = "config"
  storage_account_id    = azurerm_storage_account.strg_storageaccount.id
  container_access_type = "private"
}

# Create an Azure Storage Account for Function App Deployment
# This storage account is specifically used for storing deployment-related artifacts
# for the function app. It uses Local Redundant Storage (LRS) for cost efficiency.

resource "azurerm_storage_account" "strg_funcdep" {
  name                          = "funcdep${var.resource_suffix}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = true

  tags = { 
    azd-env-name = var.resource_suffix 
  }
}


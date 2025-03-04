# ===================================================================
# Azure Storage Account Configuration
# 
# An Azure Storage Account provides a unique namespace in Azure for 
# storing and accessing data objects such as blobs, files, queues, 
# and tables. It is a fundamental building block for cloud storage 
# solutions, offering scalable, durable, and secure storage options.
# 
# Purpose in Infrastructure:
# - Stores data for Azure Function Apps, such as input and output 
#   data, logs, and configuration files.
# - Supports various storage types, including Blob, File, Queue, 
#   and Table storage, to meet diverse application needs.
# - Configured with a private access type to ensure data security 
#   and restrict public access.
# 
# In this configuration, the Storage Account is set up with a 
# private container access type, ensuring that only authenticated 
# requests can access the stored data.
# ===================================================================

# Create an Azure Storage Account

resource "azurerm_storage_account" "strg_storageaccount" {
  name                          = "storage${var.resource_suffix}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS" # Changed from GRS to LRS for cost efficiency
  public_network_access_enabled = true
}

# Create a Blob Container for Function App Configurations

resource "azurerm_storage_container" "config_container" {
  name                  = "config"
  storage_account_id    = azurerm_storage_account.strg_storageaccount.id
  container_access_type = "private"
}

# Create an Azure Storage Account

resource "azurerm_storage_account" "strg_funcdep" {
  name                          = "funcdep${var.resource_suffix}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS" # Changed from GRS to LRS for cost efficiency
  public_network_access_enabled = true
}


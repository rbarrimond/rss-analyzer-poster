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


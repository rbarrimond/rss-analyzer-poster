# Create an Azure Cosmos DB account with a MongoDB API

resource "azurerm_cosmosdb_account" "cosmos_cosmosdb" {
  name                = "cosmosdb${var.resource_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "MongoDB"

  consistency_policy {
    consistency_level       = "BoundedStaleness"
    max_interval_in_seconds = 300
    max_staleness_prefix    = 100000
  }

  geo_location {
    location          = "eastus"
    failover_priority = 0
  }

  public_network_access_enabled = true
}

# Create a MongoDB database

resource "azurerm_cosmosdb_mongo_database" "cosmos_cosmosdbmongo" {
  name                = "mongo${var.resource_suffix}"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos_cosmosdb.name
  throughput          = 400
}


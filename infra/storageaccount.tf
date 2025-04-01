# ===================================================================
# Azure Storage Account Configuration
#
# This file defines the configuration for Azure Storage Accounts used
# in the RSS Analyzer Poster project. It includes:
# - A general-purpose storage account for application data.
# - A blob container for storing function app configuration files.
# - A dedicated storage account for function app deployment artifacts.
# ===================================================================

# General-purpose storage account for app data.
resource "azurerm_storage_account" "strg_storageaccount" {
  name                          = "storage${var.resource_suffix}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"

  tags = { 
    azd-env-name = var.resource_suffix 
  }
}

# Role assignment for admin contributor.
resource "azurerm_role_assignment" "admin_storage_table_data_contributor" {
  principal_id         = var.admin_object_id
  role_definition_name = "Storage Table Data Contributor"
  scope                = azurerm_storage_account.strg_storageaccount.id
}

# Blob container for function app config.
resource "azurerm_storage_container" "config_container" {
  name                  = var.config_container
  storage_account_id    = azurerm_storage_account.strg_storageaccount.id
  container_access_type = "private"
}

# Blob container for storing full RSS entries.
resource "azurerm_storage_container" "rss_entries_container" {
  name                  = var.rss_entries_container
  storage_account_id    = azurerm_storage_account.strg_storageaccount.id
  container_access_type = "private"
}

# Storage table for RSS feed info.
resource "azurerm_storage_table" "rss_feeds_table" {
  name                 = var.rss_feeds_table
  storage_account_name = azurerm_storage_account.strg_storageaccount.name
}

# Storage table for RSS entries.
resource "azurerm_storage_table" "rss_entries_table" {
  name                 = var.rss_entries_table
  storage_account_name = azurerm_storage_account.strg_storageaccount.name
}

# Storage table for AI enrichment data.
resource "azurerm_storage_table" "ai_enrichment_table" {
  name                 = var.ai_enrichment_table
  storage_account_name = azurerm_storage_account.strg_storageaccount.name
}

# Storage table for RSS posts.
resource "azurerm_storage_table" "posts_table" {
  name                 = var.posts_table
  storage_account_name = azurerm_storage_account.strg_storageaccount.name
}

# Storage queue for RSS feeds.
resource "azurerm_storage_queue" "rss_feed_queue" {
  name                 = var.rss_feed_queue
  storage_account_name = azurerm_storage_account.strg_storageaccount.name
}

# Storage queue for RSS entries.
resource "azurerm_storage_queue" "rss_entry_queue" {
  name                 = var.rss_entries_queue
  storage_account_name = azurerm_storage_account.strg_storageaccount.name
}

# Storage account for function app deployment artifacts.
resource "azurerm_storage_account" "strg_funcdep" {
  name                          = "funcdep${var.resource_suffix}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  
  # Enable private access settings for the storage account
  public_network_access_enabled = false
  network_rules {
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
  }

  tags = { 
    azd-env-name = var.resource_suffix 
  }
}

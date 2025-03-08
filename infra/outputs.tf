# ===================================================================
# Terraform Outputs
# This file defines the outputs for various Azure resources managed
# by Terraform. These outputs provide resource IDs and other values
# that can be used for reference in other configurations or scripts.
# ===================================================================

# # Output for the RSS Feed Downloader Function App ID
# output "function_app_rssfeeddownloader_id" {
#   value = azurerm_linux_function_app.func_rssfeeddownloader.id
# }

# Output for the Storage Account Blob Endpoint
output "storage_account_blob_endpoint" {
  value = azurerm_storage_account.strg_storageaccount.primary_blob_endpoint
}

# Output for the Storage Account Table Endpoint
output "storage_account_table_endpoint" {
  value = azurerm_storage_account.strg_storageaccount.primary_table_endpoint
}

# Output for the Storage Account Queue Endpoint
output "storage_account_queue_endpoint" {
  value = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
}

# Output for the Storage Account File Endpoint
output "storage_account_file_endpoint" {
  value = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
}

# Output for the Storage Account URL
output "storage_account_url" {
  value = "https://${azurerm_storage_account.strg_storageaccount.name}.blob.core.windows.net"
}

# Output for the Cosmos DB Name
output "cosmos_db_name" {
  value = "mongo${var.resource_suffix}"
}

# Output for the Cosmos DB Container Name
output "cosmos_db_container" {
  value = "rss_feeds"
}

# Output for the Application Insights Connection String
output "applicationinsights_connection_string" {
  value     = azurerm_application_insights.app_insights.connection_string
  sensitive = true
}

# Output for the RSS Analyzer Poster Function App ID
output "function_app_rss_analyzer_poster_id" {
  value = azurerm_linux_function_app.rss_analyzer_poster.id
}

# Output for the Storage Account ID (General Storage)
output "storage_account_storageaccount_id" {
  value = azurerm_storage_account.strg_storageaccount.id
}

# Output for the Storage Account ID (Function Deployment)
output "storage_account_funcdep_id" {
  value = azurerm_storage_account.strg_funcdep.id
}


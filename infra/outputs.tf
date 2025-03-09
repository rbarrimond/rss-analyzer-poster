# ===================================================================
# Terraform Outputs
# This file defines the outputs for various Azure resources managed
# by Terraform. These outputs provide resource IDs and other values
# that can be used for reference in other configurations or scripts.
# ===================================================================

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
  description = "The primary queue endpoint for the storage account."
  value       = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
}

# Output for the Storage Account File Endpoint
output "storage_account_file_endpoint" {
  description = "The primary file endpoint for the storage account."
  value       = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
}

# Output for the RSS Analyzer Poster Function App Name
output "function_app_rss_analyzer_poster_name" {
  description = "The name of the RSS Analyzer Poster Function App."
  value       = azurerm_linux_function_app.rss_analyzer_poster.name
}

# Output for the RSS Analyzer Poster Function App Default Hostname
output "function_app_rss_analyzer_poster_default_hostname" {
  description = "The default hostname for the RSS Analyzer Poster Function App."
  value       = azurerm_linux_function_app.rss_analyzer_poster.default_hostname
}

# Output for the RSS Analyzer Poster Function App URL
output "function_app_rss_analyzer_poster_url" {
  description = "The URL for accessing the RSS Analyzer Poster Function App."
  value       = "https://${azurerm_linux_function_app.rss_analyzer_poster.default_hostname}"
}

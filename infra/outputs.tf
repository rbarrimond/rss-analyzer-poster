# ===================================================================
# Terraform Outputs
# This file defines the outputs for various Azure resources managed
# by Terraform. These outputs provide resource IDs that can be used
# for reference in other configurations or scripts.
# ===================================================================

# Output for the RSS Feed Downloader Function App ID
output "function_app_rssfeeddownloader_id" {
  value = azurerm_linux_function_app.func_rssfeeddownloader.id
}

# Output for the Content Summarizer Function App ID
output "function_app_contentsummarizer_id" {
  value = azurerm_linux_function_app.func_contentsummarizer.id
}

# Output for the Content Ranker Function App ID
output "function_app_contentranker_id" {
  value = azurerm_linux_function_app.func_contentranker.id
}

# Output for the LinkedIn Post Suggester Function App ID
output "function_app_linkedinpostsuggester_id" {
  value = azurerm_linux_function_app.func_linkedinpostsuggester.id
}

# Output for the Storage Account ID (General Storage)
output "storage_account_storageaccount_id" {
  value = azurerm_storage_account.strg_storageaccount.id
}

# Output for the Cosmos DB Account ID
output "cosmos_account_cosmosdb_id" {
  value = azurerm_cosmosdb_account.cosmos_cosmosdb.id
}

# Output for the Storage Account ID (Function Deployment)
output "storage_account_funcdep_id" {
  value = azurerm_storage_account.strg_funcdep.id
}


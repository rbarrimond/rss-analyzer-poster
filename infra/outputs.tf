output "function_app_rssfeeddownloader_id" {
  value = azurerm_linux_function_app.func_rssfeeddownloader.id
}

output "function_app_contentsummarizer_id" {
  value = azurerm_linux_function_app.func_contentsummarizer.id
}

output "function_app_contentranker_id" {
  value = azurerm_linux_function_app.func_contentranker.id
}

output "function_app_linkedinpostsuggester_id" {
  value = azurerm_linux_function_app.func_linkedinpostsuggester.id
}

output "storage_account_storageaccount_id" {
  value = azurerm_storage_account.strg_storageaccount.id
}

output "cosmos_account_cosmosdb_id" {
  value = azurerm_cosmosdb_account.cosmos_cosmosdb.id
}

output "storage_account_funcdep_id" {
  value = azurerm_storage_account.strg_funcdep.id
}


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

# Output for the Main AI Account Endpoint
output "main_ai_account_endpoint" {
  description = "The endpoint for the main AI account."
  value       = azurerm_cognitive_account.main.endpoint
}

# Output for the GPT-35 Turbo Deployment Name
output "gpt35_turbo_deployment_name" {
  description = "The name of the GPT-35 Turbo deployment."
  value       = azurerm_cognitive_deployment.gpt35_turbo.name
}

# Output for the GPT-35 Turbo Deployment Version
output "gpt35_turbo_deployment_version" {
  description = "The version of the GPT-35 Turbo deployment."
  value       = azurerm_cognitive_deployment.gpt35_turbo.model[0].version
}

# Output for the GPT-4o Deployment Name
output "gpt4o_deployment_name" {
  description = "The name of the GPT-4o deployment."
  value       = azurerm_cognitive_deployment.gpt4o.name
}

# Output for the GPT-4o Deployment Version
output "gpt4o_deployment_version" {
  description = "The version of the GPT-4o deployment."
  value       = azurerm_cognitive_deployment.gpt4o.model[0].version
}

# Output for the GPT-4o Mini Deployment Name
output "gpt4o_mini_deployment_name" {
  description = "The name of the GPT-4o Mini deployment."
  value       = azurerm_cognitive_deployment.gpt4o_mini.name
}

# Output for the GPT-4o Mini Deployment Version
output "gpt4o_mini_deployment_version" {
  description = "The version of the GPT-4o Mini deployment."
  value       = azurerm_cognitive_deployment.gpt4o_mini.model[0].version
}

# Output for the Text Embedding 3 Small Deployment Name
output "text_embedding3_small_deployment_name" {
  description = "The name of the Text Embedding 3 Small deployment."
  value       = azurerm_cognitive_deployment.text_embedding3_small.name
}

# Output for the Text Embedding 3 Small Deployment Version
output "text_embedding3_small_deployment_version" {
  description = "The version of the Text Embedding 3 Small deployment."
  value       = azurerm_cognitive_deployment.text_embedding3_small.model[0].version
}

# Output for the Text Embedding 3 Large Deployment Name
output "text_embedding3_large_deployment_name" {
  description = "The name of the Text Embedding 3 Large deployment."
  value       = azurerm_cognitive_deployment.text_embedding3_large.name
}

# Output for the Text Embedding 3 Large Deployment Version
output "text_embedding3_large_deployment_version" {
  description = "The version of the Text Embedding 3 Large deployment."
  value       = azurerm_cognitive_deployment.text_embedding3_large.model[0].version
}

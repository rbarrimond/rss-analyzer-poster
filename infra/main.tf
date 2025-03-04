# ===================================================================
# Azure Provider Configuration
# Configures the Azure provider with default settings and specifies
# the subscription ID to be used for resource management.
# ===================================================================
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# ===================================================================
# Azure Client Configuration
# Retrieves the current Azure client configuration for use in
# resource management and deployment.
# ===================================================================
data "azurerm_client_config" "current" {}

# ===================================================================
# Azure Resource Group
# Creates a resource group to contain all related Azure resources
# for the RSS Analyzer and LinkedIn Poster project.
# ===================================================================
resource "azurerm_resource_group" "rg" {
  name     = "rg${var.resource_suffix}"
  location = var.location
  tags = {
    azd-env-name = var.resource_suffix
  }
}

# ===================================================================
# Azure Application Insights
# Sets up Application Insights for monitoring and logging of
# Azure Functions and other resources.
# ===================================================================
resource "azurerm_application_insights" "app_insights" {
  name                = "appInsights${var.resource_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
}

# # ===================================================================
# # Azure Linux Function App: RSS Feed Downloader
# # Deploys a Linux-based Azure Function App for downloading RSS feeds.
# # Configures storage and service plan settings.
# # ===================================================================
# resource "azurerm_linux_function_app" "func_rssfeeddownloader" {
#   name                = "rssFeedDownloader${var.resource_suffix}"
#   resource_group_name = azurerm_resource_group.rg.name
#   location            = azurerm_resource_group.rg.location

#   storage_account_name       = azurerm_storage_account.strg_funcdep.name
#   storage_account_access_key = azurerm_storage_account.strg_funcdep.primary_access_key
#   service_plan_id            = azurerm_service_plan.funcplanlinux.id

#   site_config {
#     always_on = true
#     # Health check configuration
#     health_check_path = "/health"  # Specify the path for health checks
#     health_check_eviction_time_in_min = 10  # Specify eviction time in minutes
#   }
#   app_settings = {
#     "FUNCTIONS_WORKER_RUNTIME"              = "python"
#     "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.app_insights.connection_string
#     "AZURE_STORAGEACCOUNT_BLOBENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_blob_endpoint
#     "AZURE_STORAGEACCOUNT_TABLEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_table_endpoint
#     "AZURE_STORAGEACCOUNT_QUEUEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
#     "AZURE_STORAGEACCOUNT_FILEENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
#     "AZURE_COSMOS_DB_ENDPOINT"              = azurerm_cosmosdb_account.cosmos_cosmosdb.endpoint
#     "AZURE_COSMOS_DB_NAME"                  = azurerm_cosmosdb_mongo_database.cosmos_cosmosdbmongo.name
#     "AZURE_COSMOS_DB_CONTAINER"             = "rss_feeds"
#   }

#   identity {
#     type = "SystemAssigned"
#   }
# }

# resource "azurerm_linux_function_app" "func_contentsummarizer" {
#   name                = "contentSummarizer${var.resource_suffix}"
#   resource_group_name = azurerm_resource_group.rg.name
#   location            = azurerm_resource_group.rg.location

#   storage_account_name       = azurerm_storage_account.strg_funcdep.name
#   storage_account_access_key = azurerm_storage_account.strg_funcdep.primary_access_key
#   service_plan_id            = azurerm_service_plan.funcplanlinux.id

#   site_config {
#     always_on = true
#     # Health check configuration
#     health_check_path = "/health"  # Specify the path for health checks
#     health_check_eviction_time_in_min = 10  # Specify eviction time in minutes
#   }
#   app_settings = {
#     "FUNCTIONS_WORKER_RUNTIME"              = "python"
#     "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.app_insights.connection_string
#     "AZURE_STORAGEACCOUNT_BLOBENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_blob_endpoint
#     "AZURE_STORAGEACCOUNT_TABLEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_table_endpoint
#     "AZURE_STORAGEACCOUNT_QUEUEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
#     "AZURE_STORAGEACCOUNT_FILEENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
#     "AZURE_COSMOS_DB_ENDPOINT"              = azurerm_cosmosdb_account.cosmos_cosmosdb.endpoint
#     "AZURE_COSMOS_DB_NAME"                  = azurerm_cosmosdb_mongo_database.cosmos_cosmosdbmongo.name
#     "AZURE_COSMOS_DB_CONTAINER"             = "rss_feeds"
#   }

#   identity {
#     type = "SystemAssigned"
#   }
# }

# resource "azurerm_linux_function_app" "func_contentranker" {
#   name                = "contentRanker${var.resource_suffix}"
#   resource_group_name = azurerm_resource_group.rg.name
#   location            = azurerm_resource_group.rg.location

#   storage_account_name       = azurerm_storage_account.strg_funcdep.name
#   storage_account_access_key = azurerm_storage_account.strg_funcdep.primary_access_key
#   service_plan_id            = azurerm_service_plan.funcplanlinux.id

#   site_config {
#     always_on = true
#     # Health check configuration
#     health_check_path = "/health"  # Specify the path for health checks
#     health_check_eviction_time_in_min = 10  # Specify eviction time in minutes
#   }
#   app_settings = {
#     "FUNCTIONS_WORKER_RUNTIME"              = "python"
#     "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.app_insights.connection_string
#     "AZURE_STORAGEACCOUNT_BLOBENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_blob_endpoint
#     "AZURE_STORAGEACCOUNT_TABLEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_table_endpoint
#     "AZURE_STORAGEACCOUNT_QUEUEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
#     "AZURE_STORAGEACCOUNT_FILEENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
#     "AZURE_COSMOS_DB_ENDPOINT"              = azurerm_cosmosdb_account.cosmos_cosmosdb.endpoint
#     "AZURE_COSMOS_DB_NAME"                  = azurerm_cosmosdb_mongo_database.cosmos_cosmosdbmongo.name
#     "AZURE_COSMOS_DB_CONTAINER"             = "rss_feeds"
#   }

#   identity {
#     type = "SystemAssigned"
#   }
# }

# resource "azurerm_linux_function_app" "func_linkedinpostsuggester" {
#   name                = "linkedinPostSuggester${var.resource_suffix}"
#   resource_group_name = azurerm_resource_group.rg.name
#   location            = azurerm_resource_group.rg.location

#   storage_account_name       = azurerm_storage_account.strg_funcdep.name
#   storage_account_access_key = azurerm_storage_account.strg_funcdep.primary_access_key
#   service_plan_id            = azurerm_service_plan.funcplanlinux.id

#   site_config {
#     always_on = true
#     # Health check configuration
#     health_check_path = "/health"  # Specify the path for health checks
#     health_check_eviction_time_in_min = 10  # Specify eviction time in minutes
#   }
#   app_settings = {
#     "FUNCTIONS_WORKER_RUNTIME"              = "python"
#     "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.app_insights.connection_string
#     "AZURE_STORAGEACCOUNT_BLOBENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_blob_endpoint
#     "AZURE_STORAGEACCOUNT_TABLEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_table_endpoint
#     "AZURE_STORAGEACCOUNT_QUEUEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
#     "AZURE_STORAGEACCOUNT_FILEENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
#     "AZURE_COSMOS_DB_ENDPOINT"              = azurerm_cosmosdb_account.cosmos_cosmosdb.endpoint
#     "AZURE_COSMOS_DB_NAME"                  = azurerm_cosmosdb_mongo_database.cosmos_cosmosdbmongo.name
#     "AZURE_COSMOS_DB_CONTAINER"             = "rss_feeds"
#   }

#   identity {
#     type = "SystemAssigned"
#   }
# }

resource "azurerm_linux_function_app" "rss_analyzer_poster" {
  name                = "rssAnalyzerPoster${var.resource_suffix}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  storage_account_name       = azurerm_storage_account.strg_funcdep.name
  storage_account_access_key = azurerm_storage_account.strg_funcdep.primary_access_key
  service_plan_id            = azurerm_service_plan.funcplanlinux.id

  site_config {
    always_on = true
    # Health check configuration
    health_check_path = "/health"  # Specify the path for health checks
    health_check_eviction_time_in_min = 10  # Specify eviction time in minutes
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"              = "python"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.app_insights.connection_string
    "AZURE_STORAGEACCOUNT_BLOBENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_blob_endpoint
    "AZURE_STORAGEACCOUNT_TABLEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_table_endpoint
    "AZURE_STORAGEACCOUNT_QUEUEENDPOINT"    = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
    "AZURE_STORAGEACCOUNT_FILEENDPOINT"     = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
    "AZURE_COSMOS_DB_ENDPOINT"              = azurerm_cosmosdb_account.cosmos_cosmosdb.endpoint
    "AZURE_COSMOS_DB_NAME"                  = azurerm_cosmosdb_mongo_database.cosmos_cosmosdbmongo.name
    "AZURE_COSMOS_DB_CONTAINER"             = "rss_feeds"
  }

  identity {
    type = "SystemAssigned"
  }
}



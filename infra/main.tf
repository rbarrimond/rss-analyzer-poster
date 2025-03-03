# Use the default behaviours of the Azure Provider
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

data "azurerm_client_config" "current" {}


# Create an Azure Resource Group

resource "azurerm_resource_group" "rg" {
	name		=	"rg${var.resource_suffix}"
	location	=	var.location
	tags  		= {
		azd-env-name = var.resource_suffix
	}
}

resource "azurerm_linux_function_app" "func_rssfeeddownloader" {
    name                = "rssFeedDownloader${var.resource_suffix}"
    resource_group_name = azurerm_resource_group.rg.name
    location            = azurerm_resource_group.rg.location

    storage_account_name       = azurerm_storage_account.strg_funcdep.name
    storage_account_access_key = azurerm_storage_account.strg_funcdep.primary_access_key
    service_plan_id            = azurerm_service_plan.funcplanlinux.id

    site_config {
	}

    app_settings = { 
        "AZURE_STORAGEACCOUNT_BLOBENDPOINT" = azurerm_storage_account.strg_storageaccount.primary_blob_endpoint
        "AZURE_STORAGEACCOUNT_TABLEENDPOINT" = azurerm_storage_account.strg_storageaccount.primary_table_endpoint
        "AZURE_STORAGEACCOUNT_QUEUEENDPOINT" = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
        "AZURE_STORAGEACCOUNT_FILEENDPOINT" = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
    }

    identity {
        type = "SystemAssigned" 
    }

	
}

resource "azurerm_linux_function_app" "func_contentsummarizer" {
    name                = "contentSummarizer${var.resource_suffix}"
    resource_group_name = azurerm_resource_group.rg.name
    location            = azurerm_resource_group.rg.location

    storage_account_name       = azurerm_storage_account.strg_funcdep.name
    storage_account_access_key = azurerm_storage_account.strg_funcdep.primary_access_key
    service_plan_id            = azurerm_service_plan.funcplanlinux.id

    site_config {
	}

    app_settings = { 
        "AZURE_STORAGEACCOUNT_BLOBENDPOINT" = azurerm_storage_account.strg_storageaccount.primary_blob_endpoint
        "AZURE_STORAGEACCOUNT_TABLEENDPOINT" = azurerm_storage_account.strg_storageaccount.primary_table_endpoint
        "AZURE_STORAGEACCOUNT_QUEUEENDPOINT" = azurerm_storage_account.strg_storageaccount.primary_queue_endpoint
        "AZURE_STORAGEACCOUNT_FILEENDPOINT" = azurerm_storage_account.strg_storageaccount.primary_file_endpoint
    }

    identity {
        type = "SystemAssigned" 
    }

	
}

resource "azurerm_linux_function_app" "func_contentranker" {
    name                = "contentRanker${var.resource_suffix}"
    resource_group_name = azurerm_resource_group.rg.name
    location            = azurerm_resource_group.rg.location

    storage_account_name       = azurerm_storage_account.strg_funcdep.name
    storage_account_access_key = azurerm_storage_account.strg_funcdep.primary_access_key
    service_plan_id            = azurerm_service_plan.funcplanlinux.id

    site_config {
	}

    app_settings = { 
        "AZURE_COSMOS_RESOURCEENDPOINT" = azurerm_cosmosdb_account.cosmos_cosmosdb.endpoint
    }

    identity {
        type = "SystemAssigned" 
    }

	
}

resource "azurerm_linux_function_app" "func_linkedinpostsuggester" {
    name                = "linkedinPostSuggester${var.resource_suffix}"
    resource_group_name = azurerm_resource_group.rg.name
    location            = azurerm_resource_group.rg.location

    storage_account_name       = azurerm_storage_account.strg_funcdep.name
    storage_account_access_key = azurerm_storage_account.strg_funcdep.primary_access_key
    service_plan_id            = azurerm_service_plan.funcplanlinux.id

    site_config {
	}

    app_settings = { 
        "AZURE_COSMOS_RESOURCEENDPOINT" = azurerm_cosmosdb_account.cosmos_cosmosdb.endpoint
    }

    identity {
        type = "SystemAssigned" 
    }

	
}



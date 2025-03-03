# Create an Azure Storage Account

resource "azurerm_storage_account" "strg_storageaccount" {
	name						=	"storageAccount${var.resource_suffix}"
	resource_group_name			=	azurerm_resource_group.rg.name
	location					=	azurerm_resource_group.rg.location
	account_tier				=	"Standard"
	account_replication_type	=	"GRS"
	public_network_access_enabled = true
}

# Create an Azure Storage Account

resource "azurerm_storage_account" "strg_funcdep" {
	name						=	"funcdep${var.resource_suffix}"
	resource_group_name			=	azurerm_resource_group.rg.name
	location					=	azurerm_resource_group.rg.location
	account_tier				=	"Standard"
	account_replication_type	=	"GRS"
	public_network_access_enabled = true
}


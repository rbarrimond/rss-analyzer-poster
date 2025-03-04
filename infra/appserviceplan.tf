# ===================================================================
# Azure App Service Plan Configuration
# 
# An Azure App Service Plan defines the region, number of workers, 
# and pricing tier for an Azure App Service. It is a foundational 
# resource that determines the compute resources and scaling 
# capabilities available to the web apps, API apps, mobile apps, 
# and function apps hosted within it.
# 
# Purpose in Infrastructure:
# - Provides the compute resources for hosting Azure Function Apps.
# - Determines the pricing tier and scaling options, impacting cost 
#   and performance.
# - Supports different operating systems (Linux or Windows) and 
#   various SKUs to match the application's needs.
# 
# In this configuration, the App Service Plan is set up for Linux 
# with a Basic (B1) SKU, suitable for development and testing 
# environments with low to moderate traffic.
# ===================================================================

resource "azurerm_service_plan" "funcplanlinux" {
	name                = "funcplanlinux${var.resource_suffix}"
	resource_group_name = azurerm_resource_group.rg.name
	location            = azurerm_resource_group.rg.location
	os_type             = "Linux"
	sku_name            = "B1"
	# sku_name			= "Y1" # For when in production
}


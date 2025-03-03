resource "azurerm_service_plan" "funcplanlinux" {
	name                = "funcplanlinux${var.resource_suffix}"
	resource_group_name = azurerm_resource_group.rg.name
	location            = azurerm_resource_group.rg.location
	os_type             = "Linux"
	sku_name            = "B1"
}


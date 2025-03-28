# Resource: Azure Service Bus Namespace - creates the service bus namespace.
resource "azurerm_servicebus_namespace" "sb_namespace" {
  name                = "sb${var.resource_suffix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "Standard"
  tags = {
    azd-env-name = var.resource_suffix
  }
}

# Resource: Azure Service Bus Queue for RSS Feed Info -
#   prompts Azure Functions to process feeds modified since last checked.
resource "azurerm_servicebus_queue" "rss_feed_info_queue" {
  name                = "rssfeed"
  namespace_id      = azurerm_servicebus_namespace.sb_namespace.id
}

# Resource: Azure Service Bus Queue for RSS Feed Entries -
#   used for AI enrichment (readability, engagement, etc.).
resource "azurerm_servicebus_queue" "rss_feed_entries_queue" {
  name                = "rssfeedentries"
  namespace_id      = azurerm_servicebus_namespace.sb_namespace.id
}

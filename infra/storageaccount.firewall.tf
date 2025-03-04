# # Create firewall rules to allow traffics to access the storage account

# resource "azurerm_storage_account_network_rules" "strg_storageaccount" {
# 	storage_account_id	=	azurerm_storage_account.strg_storageaccount.id
# 	default_action		=	"Deny"
# 	ip_rules			=	concat(
# 		azurerm_linux_function_app.func_rssfeeddownloader.possible_outbound_ip_address_list,
# 		azurerm_linux_function_app.func_contentsummarizer.possible_outbound_ip_address_list
# 	)
# }


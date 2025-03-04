# # Create an Azure Role Assignment

# resource "azurerm_role_assignment" "azurestorageaccountstorageAccount" {
# 	scope					=	azurerm_storage_account.strg_storageaccount.id
# 	role_definition_name	=	"Reader and Data Access"
# 	principal_id			=	azurerm_linux_function_app.func_contentsummarizer.identity[0].principal_id
# }

# # Create an Azure Role Assignment

# resource "azurerm_role_assignment" "azurecosmosdbcosmosDB" {
# 	scope					=	azurerm_cosmosdb_account.cosmos_cosmosdb.id
# 	role_definition_name	=	"DocumentDB Account Contributor"
# 	principal_id			=	azurerm_linux_function_app.func_linkedinpostsuggester.identity[0].principal_id
# }


# ===================================================================
# Terraform Configuration
# Specifies the required providers and their sources for this
# Terraform configuration.
# ===================================================================
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=2.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~>1.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = ">=2.0"
    }
  }
}

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
# Azure API Provider Configuration
# Configures the Azure API provider with default settings. This
# provider is used to manage Azure resources that are not yet
# supported by the azurerm provider.
# ===================================================================
provider "azapi" {
  # No additional configuration required
}

# ===================================================================
# Azure AD Provider Configuration
# Configures the Azure AD provider for managing Azure Active Directory
# resources such as applications, service principals, and groups.
# ===================================================================
provider "azuread" {
  # No additional configuration required
}
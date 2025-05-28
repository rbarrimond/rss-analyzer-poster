# Terraform Configuration for Azure AD Application Setup
#
# This configuration automates the setup of an Azure Active Directory (AD) application.
# It includes the creation of an Azure AD application, a client secret, and the assignment
# of necessary permissions to access the Microsoft Graph API.
#
# Components:
# - Azure AD Application: Registers an application with a specified display name and sign-in audience.
# - Client Secret: Generates a secure password for the application with an expiration date.
# - Microsoft Graph API Permissions: Grants the application specific permissions to interact with Microsoft Graph API.
#
# Usage:
# - Ensure all required variables, such as `var.resource_suffix`, are defined in your Terraform variables file.
# - Adjust permissions and expiration dates as needed to fit your security and operational requirements.

# Retrieve well-known application IDs including Microsoft Graph API 
# No manual configuration needed, Terraform fetches the latest well-known IDs
data "azuread_application_published_app_ids" "well_known" {}

 # Retrieve the Microsoft Graph API service principal
resource "azuread_service_principal" "msgraph" {
  client_id    = data.azuread_application_published_app_ids.well_known.result.MicrosoftGraph
  use_existing = true
}

# Register an Azure Active Directory (AD) application
resource "azuread_application" "rss_feed_analyzer" {
  display_name     = "RSS Feed Analyzer-Poster" # Display name of the app registration
  sign_in_audience = "AzureADMyOrg"             # Restrict sign-in to the organization only

  # Assign Microsoft Graph API, Mail required permissions to the application
  required_resource_access {
    resource_app_id = data.azuread_application_published_app_ids.well_known.result.MicrosoftGraph

    resource_access {
      id   = azuread_service_principal.msgraph.app_role_ids["Sites.ReadWrite.All"]
      type = "Role"
    }

    resource_access {
      id   = azuread_service_principal.msgraph.app_role_ids["Mail.Send"]
      type = "Role"
    }

    # Add Sites.Manage.All permission to allow creating lists
    resource_access {
      id   = azuread_service_principal.msgraph.app_role_ids["Sites.Manage.All"]
      type = "Role"
    }
  }

  tags = [ var.resource_suffix ] # Tag the application for easy identification
}

# Create a client secret for the application
resource "azuread_application_password" "rss_feed_secret" {
  application_id = azuread_application.rss_feed_analyzer.id # Link to the app registration
  display_name   = "secret${var.resource_suffix}"           # Name for easy identification
  end_date       = timeadd(timestamp(), "8760h")            # Set expiration date to 12 months (8760 hours) from now

  lifecycle {
    # Ignore changes to end_date to prevent unnecessary secret replacement
    # caused by minor format differences or manual updates.
    ignore_changes = [
      end_date
    ]
  }
}

# Retrieve the system managed service principal for the application in order to assign roles
# to the Function App that will use this application
resource "azuread_service_principal" "rss_feed_analyzer" {
  client_id = azuread_application.rss_feed_analyzer.client_id
  use_existing = true
}
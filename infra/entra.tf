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

# Purpose: Create an Azure AD application, client secret, service principal, and assign permissions to the Microsoft Graph API

# Register an Azure Active Directory (AD) application
resource "azuread_application" "rss_feed_analyzer" {
  display_name     = "RSS Feed Analyzer-Poster" # Display name of the app registration
  sign_in_audience = "AzureADMyOrg"             # Restrict sign-in to the organization only

  # Assign Microsoft Graph API permissions to the application
  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph API

    # Assign specific API permissions using known GUIDs
    resource_access {
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d" # User.Read (Delegated)
      type = "Scope"
    }
    resource_access {
      id   = "de4e4161-a10a-4dfd-809c-e328d89aefeb" # Directory.Read.All (Application)
      type = "Role"
    }
    resource_access {
      id   = "23c5a9bd-d900-4ecf-be26-a0689755d9e5" # User.ReadWrite.All (Application)
      type = "Role"
    }
    resource_access {
      id   = "b633e1c5-b582-4048-a93e-9f11b44c7e96" # Reports.Read.All (Application)
      type = "Role"
    }
  }
}

# Create a client secret for the application
resource "azuread_application_password" "rss_feed_secret" {
  application_id = azuread_application.rss_feed_analyzer.id # Link to the app registration
  display_name   = "secret${var.resource_suffix}"           # Name for easy identification
  end_date       = "2025-09-30T00:00:00.000Z"               # Expiration date for security best practices
}

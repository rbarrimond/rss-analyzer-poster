// This file defines the variables used in the Terraform configuration for the RSS Analyzer Poster project.
// Each variable is described with its purpose and expected type.

variable "subscription_id" {
  description = "The Azure subscription ID where resources will be deployed"
  type        = string
}

variable "resource_suffix" {
  description = "A unique suffix for naming resources to avoid naming conflicts"
  type        = string
}

variable "location" {
  description = "The Azure region where resources will be deployed"
  type        = string
}

variable "tenant_id" {
  description = "The Microsoft Entra tenant ID for authentication"
  type        = string
}

variable "admin_object_id" {
  description = "The Microsoft Entra object ID for the admin account"
  type        = string
}

variable "rssap_client_id" {
  description = "The client ID for the Rssap Azure AD application"
  type        = string
}

variable "rssap_client_secret" {
  description = "The client secret for the Rssap Azure AD application"
  type        = string
  sensitive   = true
}

variable "azure_openai_api_key" {
  description = "The API key for Azure OpenAI"
  type        = string
  sensitive   = true
}

variable "azure_openai_model" {
  description = "The model name for Azure OpenAI"
  type        = string
}

variable "azure_openai_deployment" {
  description = "The deployment name for Azure OpenAI"
  type        = string
}

variable "azure_openai_endpoint" {
  description = "The endpoint URL for Azure OpenAI"
  type        = string
}

variable "openai_api_version" {
  description = "The API version for Azure OpenAI"
  type        = string
}

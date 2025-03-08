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

variable "client_id" {
  description = "The client ID of the application or service principal used for authentication"
  type        = string
}

variable "object_id" {
  description = "The Microsoft Entra object ID for the application or service principal"
  type        = string
}


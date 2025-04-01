# This file defines the variables used in the Terraform configuration for the RSS Analyzer Poster project.
# Each variable is described with its purpose and expected type.

variable "subscription_id" {
  description = "The Azure subscription ID where resources will be deployed"
  type        = string
}

variable "resource_suffix" {
  description = "A unique suffix for naming resources to avoid naming conflicts"
  type        = string
  default     = "suf00" # Set with a unique value for your environment
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
  description = "The Microsoft Entra object ID for the administrator account"
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
variable "config_container" {
  description = "Default name for the configuration container."
  type        = string
  default     = "config"
}

variable "rss_entries_container" {
  description = "Default name for the RSS entries container."
  type        = string
  default     = "rssentries"
}

variable "rss_feeds_table" {
  description = "Default name for the RSS feeds table."
  type        = string
  default     = "rssFeeds"
}

variable "rss_entries_table" {
  description = "Default name for the RSS entries table."
  type        = string
  default     = "rssEntries"
}

variable "ai_enrichment_table" {
  description = "Default name for the AI Enrichment Table."
  type        = string
  default     = "aiEnrichment"
}

variable "posts_table" {
  description = "Default name for the Posts table."
  type        = string
  default     = "posts"
}

variable "rss_feed_queue" {
  description = "Default name for the RSS feed queue."
  type        = string
  default     = "rss-feed"
}

variable "rss_entries_queue" {
  description = "Default name for the RSS entries queue."
  type        = string
  default     = "rss-entry"
}



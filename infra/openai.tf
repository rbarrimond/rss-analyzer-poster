# ----------------------------------------------------------------------------------------------------
# Terraform Configuration for Azure OpenAI Cognitive Services
# ----------------------------------------------------------------------------------------------------
#
# Overview:
# This Terraform script automates the provisioning of an Azure Cognitive Services
# account and deploys multiple OpenAI models. Infrastructure-as-Code (IaC) ensures
# reproducibility, version control, and easier management.
#
# Project-Specific Objectives:
# - Automated Content Analysis: Process and analyze RSS feed data using AI-driven 
#   summarization, ranking, and categorization.
# - Cost-Effective AI Utilization: Deploy high-performance models for content insights 
#   while using optimized embeddings for search and ranking.
# - Scalable AI Pipeline: Support varied workloads, from lightweight ranking tasks to 
#   deeper AI-driven text analysis, ensuring efficient resource allocation.
# - Flexible Model Selection: Leverage GPT models for intelligent content extraction 
#   and embeddings for rapid search optimization.
#
# Resources Provisioned:
# 1. Azure Cognitive Services Account:
#    - Acts as a compute container for all deployed OpenAI models.
#    - Defined with a unique name, location, resource group, and SKU (S0).
#    - Costs are incurred based on SKU and model usage.
#
# 2. OpenAI Model Deployments:
#    - gpt-35-turbo: Optimized for cost-efficient text generation; used for 
#      frequent, lightweight AI tasks.
#    - gpt-4o: Latest high-performance model, selected for advanced AI-driven 
#      insights and reasoning.
#    - gpt-4o-mini: Cost-effective alternative to GPT-4o, balancing power and 
#      affordability for medium-complexity tasks.
#    - text-embedding-3-small: Fast and cost-efficient embedding model, ideal 
#      for ranking and search optimization.
#    - text-embedding-3-large: Provides richer embeddings for AI-driven 
#      categorization and deep text analysis.
#    - Each deployment is assigned a Standard SKU, incurring costs based on API usage.
#
# Naming Convention:
# - A resource_suffix variable is appended to each resource name to ensure uniqueness
#   and prevent naming conflicts across different environments.
#
# ----------------------------------------------------------------------------------------------------

resource "azurerm_cognitive_account" "main" {
  name                = "cognitiveAccount${var.resource_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "OpenAI"
  sku_name            = "S0"
}

resource "azurerm_cognitive_deployment" "gpt35_turbo" {
  name                 = "gpt35Turbo${var.resource_suffix}"
  cognitive_account_id = azurerm_cognitive_account.main.id
  model {
    format = "OpenAI"
    name   = "gpt-35-turbo"
  }

  sku {
    name = "Standard"
  }
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt4o${var.resource_suffix}"
  cognitive_account_id = azurerm_cognitive_account.main.id
  model {
    format = "OpenAI"
    name   = "gpt-4o"
  }

  sku {
    name = "Standard"
  }
}

resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = "gpt4oMini${var.resource_suffix}"
  cognitive_account_id = azurerm_cognitive_account.main.id
  model {
    format = "OpenAI"
    name   = "gpt-4o-mini"
  }

  sku {
    name = "Standard"
  }
}

resource "azurerm_cognitive_deployment" "text_embedding3_small" {
  name                 = "textEmbedding3Small${var.resource_suffix}"
  cognitive_account_id = azurerm_cognitive_account.main.id
  model {
    format = "OpenAI"
    name   = "text-embedding-3-small"
  }

  sku {
    name = "Standard"
  }
}

resource "azurerm_cognitive_deployment" "text_embedding3_large" {
  name                 = "textEmbedding3Large${var.resource_suffix}"
  cognitive_account_id = azurerm_cognitive_account.main.id
  model {
    format = "OpenAI"
    name   = "text-embedding-3-large"
  }

  sku {
    name = "Standard"
  }
}

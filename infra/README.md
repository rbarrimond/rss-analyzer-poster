# Understand the generated Terraform files

#### In this article

- [Generated file list](#generated-file-list)
- [Next steps](#next-steps)
- [Details about the generated files](#details-about-the-generated-files)

CodeToCloud generates Terraform code to create the Azure resources according to your infrastructure requirements and manages the connection between created Azure services. The generator takes care of app settings, authentication settings (identity enabling and role assignments), and public network settings to make your service work once deployed.

## Generated file list

- `main.tf`. Main entry file, see [details](#maintf).
- `variables.tf` and `main.tfvars.json`. Input parameters files, see [details](#variablestf).
- Other Terraform files. See [details](terraform-files-for-resources)
  - `cosmosdb.tf`
  - `role.tf`
  - `storageaccount.tf`
  - `storageaccount.firewall.tf`

## Next steps

1. Fill in the input parameters.
2. You could make changes to the recommended infrastructure by [Github Copilot for Azure](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azure-github-copilot). Try the following prompts in the chat window:

- @azure Replace container app with app service in the infrastructure.
- @azure Add an environment variable KEY=val to my project.
- @azure Update the environment variable KEY to \"val\" in the recommendation.

3. Provision the resources. You can refer to [Terraform Tutorials](https://developer.hashicorp.com/terraform/tutorials/cli).

## Details about the generated files

Iac Generator for Terraform generates `main.tf` to create the compute resources, `variables.tf` to take user input, and other Terraform files with the resource type name to create each resource.

### `main.tf`

This file first creates a new resource group. Compute resources such as Linux App Service, Container Apps, and Azure Functions are also created in `main.tf`. The dependency resources such as App Service Plan and Container Apps Environment are created in separate files. One kind of compute resource shares a single dependency resource. App settings and environment variables are configured based on each target resource. Implicit dependencies are used to get the necessary keys, connection strings, and principal IDs of system identity from the Terraform files of the resources.

### Terraform files for resources

For each kind of resource except the compute resources, a Terraform file with the name of the resource type creates all the instances of the service. Required parameters for resource creation are configured with some default values.

- `cosmosdb.tf` creates the instances of the Cosmos DB for Mongo with a Mongo database.

- `role.tf` creates the role assignments to grant necessary access to system identity of compute resources if identity-based connection is used.

- `storageaccount.tf` creates the instances of Storage Account.
- `storageaccount.firewall.tf` creates the instances of network rules, which add the outbound IPs of connected compute resources to the firewall rule set.

### `variables.tf` and `main.tfvars.json`

`variables.tf` contains the parameters that you can configure in `main.tfvars.json`. Replace the '<...>' placeholder with your values according to the hints provided by the variable names.

- Modify the suffix of resource group name by changing 'resource_suffix'.
- Customize the location.

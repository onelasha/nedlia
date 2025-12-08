include "root" {
  path = find_in_parent_folders()
}

locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env.hcl", "env.hcl"))
}

inputs = {
  environment         = local.env_vars.locals.environment
  aws_region          = local.env_vars.locals.aws_region
  aurora_min_capacity = local.env_vars.locals.aurora_min_capacity
  aurora_max_capacity = local.env_vars.locals.aurora_max_capacity
  lambda_memory       = local.env_vars.locals.lambda_memory
  lambda_timeout      = local.env_vars.locals.lambda_timeout
}

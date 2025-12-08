locals {
  environment = "staging"
  aws_region  = "us-east-1"

  # Environment-specific settings
  aurora_min_capacity = 1
  aurora_max_capacity = 8
  lambda_memory       = 512
  lambda_timeout      = 60
}

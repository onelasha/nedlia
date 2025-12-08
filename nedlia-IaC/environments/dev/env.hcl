locals {
  environment = "dev"
  aws_region  = "us-east-1"

  # Environment-specific settings
  aurora_min_capacity = 0.5
  aurora_max_capacity = 2
  lambda_memory       = 256
  lambda_timeout      = 30
}

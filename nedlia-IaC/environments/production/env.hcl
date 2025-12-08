locals {
  environment = "production"
  aws_region  = "us-east-1"

  # Environment-specific settings
  aurora_min_capacity = 2
  aurora_max_capacity = 64
  lambda_memory       = 1024
  lambda_timeout      = 60
}

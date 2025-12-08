locals {
  environment = "testing"
  aws_region  = "us-east-1"

  # Environment-specific settings
  aurora_min_capacity = 0.5
  aurora_max_capacity = 4
  lambda_memory       = 512
  lambda_timeout      = 30
}

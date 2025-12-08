# VPC Module
# Creates VPC, subnets, NAT gateway, and security groups

variable "environment" {
  type = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "nedlia-${var.environment}-vpc"
  }
}

output "vpc_id" {
  value = aws_vpc.main.id
}

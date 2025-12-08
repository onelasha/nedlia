# API Gateway Module
# Creates REST API Gateway

variable "environment" {
  type = string
}

variable "name" {
  type    = string
  default = "nedlia-api"
}

resource "aws_api_gateway_rest_api" "main" {
  name        = "nedlia-${var.environment}-api"
  description = "Nedlia API Gateway - ${var.environment}"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name = "nedlia-${var.environment}-api"
  }
}

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  xray_tracing_enabled = true

  tags = {
    Name = "nedlia-${var.environment}-stage"
  }
}

output "api_id" {
  value = aws_api_gateway_rest_api.main.id
}

output "api_endpoint" {
  value = aws_api_gateway_stage.main.invoke_url
}

# EventBridge Module
# Creates event bus and rules

variable "environment" {
  type = string
}

resource "aws_cloudwatch_event_bus" "main" {
  name = "nedlia-${var.environment}-events"

  tags = {
    Name = "nedlia-${var.environment}-events"
  }
}

resource "aws_schemas_discoverer" "main" {
  source_arn  = aws_cloudwatch_event_bus.main.arn
  description = "Auto-discover event schemas for Nedlia"
}

output "event_bus_name" {
  value = aws_cloudwatch_event_bus.main.name
}

output "event_bus_arn" {
  value = aws_cloudwatch_event_bus.main.arn
}

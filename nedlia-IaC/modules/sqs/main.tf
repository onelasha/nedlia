# SQS Module
# Creates SQS queue with DLQ

variable "environment" {
  type = string
}

variable "queue_name" {
  type = string
}

variable "visibility_timeout_seconds" {
  type    = number
  default = 60
}

variable "message_retention_seconds" {
  type    = number
  default = 1209600 # 14 days
}

resource "aws_sqs_queue" "dlq" {
  name                      = "nedlia-${var.environment}-${var.queue_name}-dlq"
  message_retention_seconds = var.message_retention_seconds

  tags = {
    Name = "nedlia-${var.environment}-${var.queue_name}-dlq"
  }
}

resource "aws_sqs_queue" "main" {
  name                       = "nedlia-${var.environment}-${var.queue_name}"
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name = "nedlia-${var.environment}-${var.queue_name}"
  }
}

output "queue_url" {
  value = aws_sqs_queue.main.url
}

output "queue_arn" {
  value = aws_sqs_queue.main.arn
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}

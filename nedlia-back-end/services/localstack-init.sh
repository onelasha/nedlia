#!/bin/bash
# =============================================================================
# LocalStack Initialization Script
# =============================================================================
# Creates AWS resources for local development
# =============================================================================

set -e

echo "Initializing LocalStack resources..."

# Create S3 bucket
awslocal s3 mb s3://nedlia-placements
awslocal s3 mb s3://nedlia-assets

# Create SQS queues
awslocal sqs create-queue --queue-name nedlia-file-generation
awslocal sqs create-queue --queue-name nedlia-file-generation-dlq
awslocal sqs create-queue --queue-name nedlia-validation
awslocal sqs create-queue --queue-name nedlia-validation-dlq
awslocal sqs create-queue --queue-name nedlia-notifications
awslocal sqs create-queue --queue-name nedlia-notifications-dlq

# Create EventBridge event bus
awslocal events create-event-bus --name nedlia-events

# Create EventBridge rules
awslocal events put-rule \
    --name placement-created-rule \
    --event-bus-name nedlia-events \
    --event-pattern '{"source": ["nedlia.placement-service"], "detail-type": ["placement.created"]}'

awslocal events put-rule \
    --name validation-requested-rule \
    --event-bus-name nedlia-events \
    --event-pattern '{"source": ["nedlia.api"], "detail-type": ["video.validation_requested"]}'

# Set up rule targets (SQS queues)
QUEUE_ARN=$(awslocal sqs get-queue-attributes --queue-url http://localhost:4566/000000000000/nedlia-file-generation --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
awslocal events put-targets \
    --rule placement-created-rule \
    --event-bus-name nedlia-events \
    --targets "Id=file-generation-queue,Arn=$QUEUE_ARN"

echo "LocalStack initialization complete!"
echo "S3 buckets: nedlia-placements, nedlia-assets"
echo "SQS queues: nedlia-file-generation, nedlia-validation, nedlia-notifications"
echo "EventBridge bus: nedlia-events"

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)."
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Short name used for resource naming."
  type        = string
  default     = "ig-mcp-extension"
}

variable "schedule_expression" {
  description = "EventBridge schedule for the IG metrics collector."
  type        = string
  default     = "rate(6 hours)"
}

variable "lambda_memory_size" {
  description = "Memory (MB) allocated to the Lambda function."
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Timeout (seconds) for the Lambda function."
  type        = number
  default     = 300
}

variable "lambda_image_uri" {
  description = <<EOT
Full URI of the container image to deploy (e.g. from ECR).
Example: 990207457148.dkr.ecr.us-east-1.amazonaws.com/mcp-ig-extension:20260615-120000

Best: run `make push-to-ecr` from the repo root.
EOT
  type = string
}

variable "mcp_base_url" {
  description = "Public HTTPS base URL for the deployed grok-memory-mcp Function URL."
  type        = string
}

variable "mcp_auth_secret_name" {
  description = "Secrets Manager name/ARN for the MCP Bearer token used by this extension."
  type        = string
}

variable "ig_secret_arns" {
  description = "Optional explicit IG access-token secret ARNs (in addition to the name prefix)."
  type        = list(string)
  default     = []
}

variable "ig_secrets_name_prefix" {
  description = "Secrets Manager name prefix for IG access tokens (e.g. ig/ allows ig/me2dafuture/access-token)."
  type        = string
  default     = "ig/"
}

variable "dummy_mode" {
  description = "When true, skip real Graph API calls and emit a dummy MCP write per account."
  type        = bool
  default     = true
}

variable "dry_run" {
  description = "When true, log MCP payloads without sending HTTP requests."
  type        = bool
  default     = false
}

variable "create_ecr_repository" {
  description = "Create an ECR repository for the extension image."
  type        = bool
  default     = true
}

variable "ecr_repository_name" {
  description = "ECR repository name for the extension container image."
  type        = string
  default     = "mcp-ig-extension"
}
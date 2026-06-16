output "lambda_function_name" {
  description = "Name of the deployed IG extension Lambda function"
  value       = aws_lambda_function.ig_extension.function_name
}

output "lambda_function_arn" {
  description = "ARN of the IG extension Lambda function"
  value       = aws_lambda_function.ig_extension.arn
}

output "eventbridge_rule_name" {
  description = "EventBridge schedule rule name"
  value       = aws_cloudwatch_event_rule.ig_monitor_schedule.name
}

output "ecr_repository_url" {
  description = "ECR repository URL for the extension image (if created)"
  value       = try(aws_ecr_repository.extension[0].repository_url, null)
}

output "instructions" {
  description = "Next steps after terraform apply"
  value       = <<-EOT
    1. Build and push the container image: `make push-to-ecr` from the repo root.
    2. Ensure Secrets Manager has:
       - MCP bearer token at: ${var.mcp_auth_secret_name}
       - Per-account IG tokens referenced in config/accounts.json
    3. Set mcp_base_url to your deployed grok-memory-mcp Function URL.
    4. Invoke manually to test: aws lambda invoke --function-name ${aws_lambda_function.ig_extension.function_name} /tmp/ig-out.json
    5. Check CloudWatch Logs: /aws/lambda/${aws_lambda_function.ig_extension.function_name}
    6. When ready for live Graph API calls, set dummy_mode = false in terraform.tfvars and re-apply.
  EOT
}
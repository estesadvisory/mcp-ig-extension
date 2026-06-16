data "aws_secretsmanager_secret" "mcp_auth" {
  name = var.mcp_auth_secret_name
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}"
  retention_in_days = 14
}

resource "aws_lambda_function" "ig_extension" {
  function_name = "${var.project_name}-${var.environment}"
  role          = aws_iam_role.lambda_execution.arn

  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  architectures = ["x86_64"]

  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  environment {
    variables = {
      MCP_BASE_URL           = var.mcp_base_url
      MCP_AUTH_SECRET_NAME   = var.mcp_auth_secret_name
      CONFIG_PATH            = "/var/task/config/accounts.json"
      DUMMY_MODE             = tostring(var.dummy_mode)
      DRY_RUN                = tostring(var.dry_run)
      MAX_MEDIA_PER_RUN      = "50"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.extension_access,
  ]

  tags = {
    Name = "${var.project_name}-collector"
  }
}
resource "aws_cloudwatch_event_rule" "ig_monitor_schedule" {
  name                = "${var.project_name}-schedule-${var.environment}"
  description         = "Scheduled trigger for Instagram metrics collection"
  schedule_expression = var.schedule_expression
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "ig_lambda" {
  rule      = aws_cloudwatch_event_rule.ig_monitor_schedule.name
  target_id = "IGExtensionLambda"
  arn       = aws_lambda_function.ig_extension.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ig_extension.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ig_monitor_schedule.arn
}
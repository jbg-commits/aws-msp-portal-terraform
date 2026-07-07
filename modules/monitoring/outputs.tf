output "alarm_names" {
  description = "Names of the CloudWatch Alarms that gate CodeDeploy's automatic rollback"
  value       = [aws_cloudwatch_metric_alarm.unhealthy_hosts.alarm_name, aws_cloudwatch_metric_alarm.target_5xx.alarm_name]
}

output "app_log_group_name" {
  description = "CloudWatch Log Group the app's stdout/stderr is streamed to"
  value       = aws_cloudwatch_log_group.app.name
}

output "codedeploy_agent_log_group_name" {
  description = "CloudWatch Log Group the CodeDeploy agent's log is streamed to"
  value       = aws_cloudwatch_log_group.codedeploy_agent.name
}

output "cw_agent_config_parameter_name" {
  description = "SSM Parameter name holding the CloudWatch Agent config"
  value       = aws_ssm_parameter.cw_agent_config.name
}

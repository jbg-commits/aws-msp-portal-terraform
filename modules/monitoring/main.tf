# ── Log groups ─────────────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "app" {
  name              = "/${var.project_name}/app"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-app-logs"
  }
}

resource "aws_cloudwatch_log_group" "codedeploy_agent" {
  name              = "/${var.project_name}/codedeploy-agent"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-codedeploy-agent-logs"
  }
}

# ── CloudWatch Agent: IAM + config (fetched by the instance via SSM) ─────────

resource "aws_iam_role_policy_attachment" "cw_agent" {
  role       = var.ec2_role_name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_ssm_parameter" "cw_agent_config" {
  name = "/${var.project_name}/cwagent-config"
  type = "String"

  value = jsonencode({
    logs = {
      logs_collected = {
        files = {
          collect_list = [
            {
              file_path       = "/var/log/${var.project_name}/app.log"
              log_group_name  = aws_cloudwatch_log_group.app.name
              log_stream_name = "{instance_id}"
            },
            {
              file_path       = "/var/log/aws/codedeploy-agent/codedeploy-agent.log"
              log_group_name  = aws_cloudwatch_log_group.codedeploy_agent.name
              log_stream_name = "{instance_id}"
            }
          ]
        }
      }
    }
  })
}

# ── Alarms: gate CodeDeploy's automatic rollback ──────────────────────────────

resource "aws_cloudwatch_metric_alarm" "unhealthy_hosts" {
  alarm_name          = "${var.project_name}-unhealthy-hosts"
  alarm_description   = "Target group has unhealthy hosts"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = var.unhealthy_host_threshold
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }

  tags = {
    Name = "${var.project_name}-unhealthy-hosts"
  }
}

resource "aws_cloudwatch_metric_alarm" "target_5xx" {
  alarm_name          = "${var.project_name}-target-5xx"
  alarm_description   = "App is returning 5xx responses"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = var.target_5xx_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }

  tags = {
    Name = "${var.project_name}-target-5xx"
  }
}

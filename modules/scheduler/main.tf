data "aws_caller_identity" "current" {}

# ── IAM role EventBridge Scheduler assumes to stop/start EC2 + RDS ────────────

resource "aws_iam_role" "scheduler" {
  name = "${var.project_name}-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "scheduler.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.project_name}-scheduler-role"
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${var.project_name}-scheduler-policy"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EC2StartStop"
        Effect   = "Allow"
        Action   = ["ec2:StartInstances", "ec2:StopInstances"]
        Resource = "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:instance/${var.ec2_instance_id}"
      },
      {
        Sid      = "RDSStartStop"
        Effect   = "Allow"
        Action   = ["rds:StartDBInstance", "rds:StopDBInstance"]
        Resource = "arn:aws:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:db:${var.rds_instance_identifier}"
      }
    ]
  })
}

# ── Stop app instance + database at end of business day (weekdays) ───────────

resource "aws_scheduler_schedule" "stop_ec2" {
  name       = "${var.project_name}-stop-ec2"
  group_name = "default"
  state      = var.schedule_state

  schedule_expression          = var.stop_schedule_expression
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ec2:stopInstances"
    role_arn = aws_iam_role.scheduler.arn

    input = jsonencode({
      InstanceIds = [var.ec2_instance_id]
    })
  }
}

resource "aws_scheduler_schedule" "stop_rds" {
  name       = "${var.project_name}-stop-rds"
  group_name = "default"
  state      = var.schedule_state

  schedule_expression          = var.stop_schedule_expression
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:rds:stopDBInstance"
    role_arn = aws_iam_role.scheduler.arn

    input = jsonencode({
      DbInstanceIdentifier = var.rds_instance_identifier
    })
  }
}

# ── Start app instance + database at the beginning of business day (weekdays) ─

resource "aws_scheduler_schedule" "start_ec2" {
  name       = "${var.project_name}-start-ec2"
  group_name = "default"
  state      = var.schedule_state

  schedule_expression          = var.start_schedule_expression
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ec2:startInstances"
    role_arn = aws_iam_role.scheduler.arn

    input = jsonencode({
      InstanceIds = [var.ec2_instance_id]
    })
  }
}

resource "aws_scheduler_schedule" "start_rds" {
  name       = "${var.project_name}-start-rds"
  group_name = "default"
  state      = var.schedule_state

  schedule_expression          = var.start_schedule_expression
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:rds:startDBInstance"
    role_arn = aws_iam_role.scheduler.arn

    input = jsonencode({
      DbInstanceIdentifier = var.rds_instance_identifier
    })
  }
}

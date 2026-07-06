output "scheduler_role_arn" {
  description = "IAM role ARN EventBridge Scheduler assumes to start/stop EC2 and RDS"
  value       = aws_iam_role.scheduler.arn
}

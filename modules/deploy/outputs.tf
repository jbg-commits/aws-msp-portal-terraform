output "codedeploy_app_name" {
  description = "Name of the CodeDeploy application"
  value       = aws_codedeploy_app.this.name
}

output "deployment_group_name" {
  description = "Name of the CodeDeploy deployment group"
  value       = aws_codedeploy_deployment_group.this.deployment_group_name
}

output "artifacts_bucket_name" {
  description = "S3 bucket for deployment bundles"
  value       = aws_s3_bucket.artifacts.bucket
}

output "codedeploy_service_role_arn" {
  description = "ARN of the CodeDeploy service role"
  value       = aws_iam_role.codedeploy.arn
}

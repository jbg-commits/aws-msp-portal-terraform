output "codebuild_project_name" {
  description = "Name of the CodeBuild project"
  value       = aws_codebuild_project.app.name
}

output "codebuild_role_arn" {
  description = "IAM role ARN CodeBuild assumes"
  value       = aws_iam_role.codebuild.arn
}

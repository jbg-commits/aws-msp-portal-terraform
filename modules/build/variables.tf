variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "github_repo_url" {
  description = "HTTPS URL of the GitHub repo CodeBuild pulls source from"
  type        = string
}

variable "github_branch" {
  description = "Branch that triggers a build on push"
  type        = string
  default     = "main"
}

variable "artifacts_bucket_name" {
  description = "S3 bucket name to upload the deployment bundle to"
  type        = string
}

variable "artifacts_bucket_arn" {
  description = "S3 bucket ARN to upload the deployment bundle to"
  type        = string
}

variable "codedeploy_app_name" {
  description = "Name of the CodeDeploy application to deploy to"
  type        = string
}

variable "codedeploy_deployment_group_name" {
  description = "Name of the CodeDeploy deployment group to deploy to"
  type        = string
}

variable "compute_type" {
  description = "CodeBuild compute size"
  type        = string
  default     = "BUILD_GENERAL1_SMALL"
}

variable "build_image" {
  description = "CodeBuild managed build image"
  type        = string
  default     = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
}

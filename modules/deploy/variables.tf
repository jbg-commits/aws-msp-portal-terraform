variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "target_group_name" {
  description = "ALB target group name for deployment group traffic control"
  type        = string
}

variable "alarm_names" {
  description = "CloudWatch Alarm names that trigger automatic rollback when in ALARM state"
  type        = list(string)
  default     = []
}

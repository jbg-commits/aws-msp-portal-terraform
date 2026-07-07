variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
}

variable "alb_arn_suffix" {
  description = "ARN suffix of the ALB (for CloudWatch metric dimensions)"
  type        = string
}

variable "target_group_arn_suffix" {
  description = "ARN suffix of the target group (for CloudWatch metric dimensions)"
  type        = string
}

variable "ec2_role_name" {
  description = "Name of the EC2 instance IAM role to grant CloudWatch Agent permissions"
  type        = string
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch Logs"
  type        = number
  default     = 14
}

variable "unhealthy_host_threshold" {
  description = "Number of consecutive 1-minute periods with unhealthy hosts before alarming"
  type        = number
  default     = 2
}

variable "target_5xx_threshold" {
  description = "Number of target-origin 5xx responses in a 1-minute period before alarming"
  type        = number
  default     = 5
}

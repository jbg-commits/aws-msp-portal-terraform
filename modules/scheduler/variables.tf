variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
}

variable "aws_region" {
  description = "AWS region for this project"
  type        = string
}

variable "ec2_instance_id" {
  description = "ID of the EC2 instance to start/stop on a schedule"
  type        = string
}

variable "rds_instance_identifier" {
  description = "Identifier of the RDS instance to start/stop on a schedule"
  type        = string
}

variable "schedule_timezone" {
  description = "IANA timezone the cron expressions below are evaluated in"
  type        = string
  default     = "America/New_York"
}

variable "stop_schedule_expression" {
  description = "EventBridge Scheduler cron expression for stopping the instance/database"
  type        = string
  default     = "cron(0 20 ? * MON-FRI *)"
}

variable "start_schedule_expression" {
  description = "EventBridge Scheduler cron expression for starting the instance/database"
  type        = string
  default     = "cron(0 7 ? * MON-FRI *)"
}

variable "schedule_state" {
  description = "ENABLED or DISABLED - set to DISABLED to pause all start/stop automation without removing it"
  type        = string
  default     = "ENABLED"
}

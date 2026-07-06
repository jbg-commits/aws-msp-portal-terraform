variable "aws_region" {
  description = "AWS region for this project"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "msp-portal"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_a_cidr" {
  description = "CIDR block for public subnet A"
  type        = string
  default     = "10.0.1.0/24"
}

variable "public_subnet_b_cidr" {
  description = "CIDR block for public subnet B"
  type        = string
  default     = "10.0.2.0/24"
}

variable "private_app_subnet_a_cidr" {
  description = "CIDR block for private app subnet A"
  type        = string
  default     = "10.0.11.0/24"
}

variable "private_app_subnet_b_cidr" {
  description = "CIDR block for private app subnet B"
  type        = string
  default     = "10.0.12.0/24"
}

variable "private_db_subnet_a_cidr" {
  description = "CIDR block for private DB subnet A"
  type        = string
  default     = "10.0.21.0/24"
}

variable "private_db_subnet_b_cidr" {
  description = "CIDR block for private DB subnet B"
  type        = string
  default     = "10.0.22.0/24"
}

variable "az_a" {
  description = "Availability Zone for A subnets"
  type        = string
  default     = "us-east-1a"
}

variable "az_b" {
  description = "Availability Zone for B subnets"
  type        = string
  default     = "us-east-1b"
}

variable "app_port" {
  description = "Port the application listens on"
  type        = number
  default     = 8080
}

variable "db_port" {
  description = "Port the database listens on"
  type        = number
  default     = 5432
}

variable "instance_type" {
  description = "EC2 instance type for the app server"
  type        = string
  default     = "t3.micro"
}

variable "db_name" {
  description = "Name of the initial database to create"
  type        = string
  default     = "mspportal"
}

variable "db_username" {
  description = "Master username for the RDS instance"
  type        = string
  default     = "dbadmin"
}

variable "db_password" {
  description = "Master password for the RDS instance"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "enable_scheduler" {
  description = "Whether to auto-stop/start the EC2 instance and RDS database on a business-hours schedule"
  type        = bool
  default     = true
}

variable "schedule_timezone" {
  description = "IANA timezone the scheduler cron expressions are evaluated in"
  type        = string
  default     = "America/New_York"
}

variable "stop_schedule_expression" {
  description = "EventBridge Scheduler cron expression for stopping the EC2 instance and RDS database"
  type        = string
  default     = "cron(0 20 ? * MON-FRI *)"
}

variable "start_schedule_expression" {
  description = "EventBridge Scheduler cron expression for starting the EC2 instance and RDS database"
  type        = string
  default     = "cron(0 7 ? * MON-FRI *)"
}

variable "monthly_budget_limit_usd" {
  description = "Monthly AWS cost budget limit in USD"
  type        = string
  default     = "15"
}

variable "budget_alert_email" {
  description = "Email address to notify when spend crosses the budget alert thresholds"
  type        = string
  default     = "josephbgillespie@pm.me"
}
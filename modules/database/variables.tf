variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
}

variable "db_subnet_ids" {
  description = "List of private DB subnet IDs for the subnet group"
  type        = list(string)
}

variable "db_security_group_id" {
  description = "Security group ID to attach to the RDS instance"
  type        = string
}

variable "db_name" {
  description = "Name of the initial database to create"
  type        = string
}

variable "db_username" {
  description = "Master username for the RDS instance"
  type        = string
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

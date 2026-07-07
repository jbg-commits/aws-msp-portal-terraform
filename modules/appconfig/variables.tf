variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
}

variable "ec2_role_name" {
  description = "Name of the EC2 instance IAM role to grant SSM parameter read access"
  type        = string
}

variable "db_endpoint" {
  description = "RDS endpoint (host:port) the app connects to"
  type        = string
}

variable "db_name" {
  description = "Database name the app connects to"
  type        = string
}

variable "cookie_secure" {
  description = "Whether session cookies should be marked Secure (requires HTTPS on the ALB)"
  type        = bool
  default     = false
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "public_subnet_a_cidr" {
  description = "CIDR block for public subnet A"
  type        = string
}

variable "public_subnet_b_cidr" {
  description = "CIDR block for public subnet B"
  type        = string
}

variable "private_app_subnet_a_cidr" {
  description = "CIDR block for private app subnet A"
  type        = string
}

variable "private_app_subnet_b_cidr" {
  description = "CIDR block for private app subnet B"
  type        = string
}

variable "private_db_subnet_a_cidr" {
  description = "CIDR block for private DB subnet A"
  type        = string
}

variable "private_db_subnet_b_cidr" {
  description = "CIDR block for private DB subnet B"
  type        = string
}

variable "az_a" {
  description = "Availability Zone for A subnets"
  type        = string
}

variable "az_b" {
  description = "Availability Zone for B subnets"
  type        = string
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

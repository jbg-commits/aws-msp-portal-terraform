variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
}

variable "monthly_limit_usd" {
  description = "Monthly cost budget limit in USD"
  type        = string
  default     = "15"
}

variable "alert_email" {
  description = "Email address to notify when spend crosses the alert thresholds"
  type        = string
}

variable "alert_thresholds_percent" {
  description = "Percentages of the monthly limit at which to send an actual-spend alert"
  type        = list(number)
  default     = [50, 80]
}

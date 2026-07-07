output "app_db_url_parameter_name" {
  description = "SSM parameter name holding the app's runtime (msp_app) DB connection string"
  value       = aws_ssm_parameter.app_db_url.name
}

output "db_admin_url_parameter_name" {
  description = "SSM parameter name holding the migrator (dbadmin) DB connection string -- set manually via aws ssm put-parameter"
  value       = aws_ssm_parameter.db_admin_url.name
}

output "cookie_secure_parameter_name" {
  description = "SSM parameter name holding the cookie_secure flag"
  value       = aws_ssm_parameter.cookie_secure.name
}

output "msp_app_db_password" {
  description = "Generated password for the msp_app Postgres role -- needed once for the manual CREATE ROLE bootstrap step"
  value       = random_password.msp_app_db_password.result
  sensitive   = true
}

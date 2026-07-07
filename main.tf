module "network" {
  source = "./modules/network"

  project_name              = var.project_name
  vpc_cidr                  = var.vpc_cidr
  public_subnet_a_cidr      = var.public_subnet_a_cidr
  public_subnet_b_cidr      = var.public_subnet_b_cidr
  private_app_subnet_a_cidr = var.private_app_subnet_a_cidr
  private_app_subnet_b_cidr = var.private_app_subnet_b_cidr
  private_db_subnet_a_cidr  = var.private_db_subnet_a_cidr
  private_db_subnet_b_cidr  = var.private_db_subnet_b_cidr
  az_a                      = var.az_a
  az_b                      = var.az_b
  app_port                  = var.app_port
  db_port                   = var.db_port
}

module "deploy" {
  source = "./modules/deploy"

  project_name      = var.project_name
  aws_region        = var.aws_region
  target_group_name = module.compute.target_group_name
  alarm_names       = module.monitoring.alarm_names
}

module "database" {
  source = "./modules/database"

  project_name         = var.project_name
  db_subnet_ids        = [module.network.private_db_subnet_a_id, module.network.private_db_subnet_b_id]
  db_security_group_id = module.network.db_security_group_id
  db_name              = var.db_name
  db_username          = var.db_username
  db_password          = var.db_password
  db_instance_class    = var.db_instance_class
}

module "compute" {
  source = "./modules/compute"

  project_name          = var.project_name
  vpc_id                = module.network.vpc_id
  public_subnet_ids     = [module.network.public_subnet_a_id, module.network.public_subnet_b_id]
  private_app_subnet_id = module.network.private_app_subnet_a_id
  alb_security_group_id = module.network.alb_security_group_id
  app_security_group_id = module.network.app_security_group_id
  app_port              = var.app_port
  instance_type         = var.instance_type
  aws_region            = var.aws_region
}

module "monitoring" {
  source = "./modules/monitoring"

  project_name            = var.project_name
  alb_arn_suffix          = module.compute.alb_arn_suffix
  target_group_arn_suffix = module.compute.target_group_arn_suffix
  ec2_role_name           = module.compute.ec2_role_name
  log_retention_days      = var.log_retention_days
}

module "scheduler" {
  source = "./modules/scheduler"
  count  = var.enable_scheduler ? 1 : 0

  project_name              = var.project_name
  aws_region                = var.aws_region
  ec2_instance_id           = module.compute.instance_id
  rds_instance_identifier   = module.database.db_identifier
  schedule_timezone         = var.schedule_timezone
  stop_schedule_expression  = var.stop_schedule_expression
  start_schedule_expression = var.start_schedule_expression
}

module "budget" {
  source = "./modules/budget"

  project_name      = var.project_name
  monthly_limit_usd = var.monthly_budget_limit_usd
  alert_email       = var.budget_alert_email
}

module "build" {
  source = "./modules/build"

  project_name                     = var.project_name
  aws_region                       = var.aws_region
  github_repo_url                  = var.github_repo_url
  github_branch                    = var.github_branch
  artifacts_bucket_name            = module.deploy.artifacts_bucket_name
  artifacts_bucket_arn             = module.deploy.artifacts_bucket_arn
  codedeploy_app_name              = module.deploy.codedeploy_app_name
  codedeploy_deployment_group_name = module.deploy.deployment_group_name
}
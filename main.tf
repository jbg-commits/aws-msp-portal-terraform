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
module "networking" {
  source   = "./modules/networking"
  vpc_cidr = var.vpc_cidr
}

module "dynamodb" {
  source       = "./modules/dynamodb"
  table_prefix = var.table_prefix
}

module "ecr" {
  source = "./modules/ecr"
}

module "iam" {
  source              = "./modules/iam"
  tasks_table_arn     = module.dynamodb.tasks_table_arn
  events_table_arn    = module.dynamodb.events_table_arn
  dedup_table_arn     = module.dynamodb.dedup_table_arn
  cycles_table_arn    = module.dynamodb.cycles_table_arn
  ecr_repository_arn  = module.ecr.repository_arn
  log_group_bot_arn   = module.monitoring.log_group_bot_arn
}

module "monitoring" {
  source = "./modules/monitoring"
}

module "ecs" {
  source                  = "./modules/ecs"
  image_uri               = "${module.ecr.repository_url}:${var.image_tag}"
  task_execution_role_arn = module.iam.task_execution_role_arn
  task_role_arn           = module.iam.task_role_arn
  subnet_ids              = module.networking.public_subnet_ids
  ecs_security_group_id   = module.networking.ecs_security_group_id
  log_group_name          = module.monitoring.log_group_bot_name
  telegram_bot_token      = var.telegram_bot_token
  table_prefix            = var.table_prefix
  aws_region              = var.aws_region
}

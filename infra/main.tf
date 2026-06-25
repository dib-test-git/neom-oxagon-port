terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
  backend "s3" {
    bucket = "neom-oxagon-tfstate"
    key    = "platform/main.tfstate"
    region = "me-south-1"
  }
}

provider "aws" {
  region = "me-south-1" # Bahrain — primary for KSA workloads
}

module "kafka" {
  source = "./modules/msk"

  cluster_name     = "oxagon-platform"
  kafka_version    = "3.7.1"
  broker_instance  = "kafka.m7g.large"
  broker_count     = 3
  topics = {
    "oxagon.shipments.master.v1"     = { partitions = 12, retention_ms = 604800000 }
    "oxagon.shipments.events.v1"     = { partitions = 12, retention_ms = 604800000 }
    "oxagon.yard.gate.events.v1"     = { partitions = 24, retention_ms = 1209600000 }
    "oxagon.yard.move.events.v1"     = { partitions = 24, retention_ms = 1209600000 }
    "oxagon.metrics.dwell.v1"        = { partitions = 6,  retention_ms = 604800000 }
  }
}

module "postgres" {
  source                 = "./modules/rds"
  identifier             = "oxagon-platform"
  engine_version         = "16.4"
  instance_class         = "db.r7g.2xlarge"
  allocated_storage_gb   = 500
  multi_az               = true
  performance_insights   = true
}

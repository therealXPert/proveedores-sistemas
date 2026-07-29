terraform {
  backend "gcs" {
    bucket = "AUTOCITY_PROJECT_ID-tfstate"
    prefix = "control-gasto-sistemas/dev"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

terraform {
  backend "gcs" {
    bucket = "testing-grounds-324602-tfstate"
    prefix = "testing-grounds-324602-tfstate/dev"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

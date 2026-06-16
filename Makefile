.PHONY: help install install-dev test lint build-image clean tf-init tf-plan tf-apply ecr-login push-to-ecr push-image

PYTHON_OK := $(shell for p in python3.11 python3.12 python3.13 python python3; do if $$p -c 'import sys; v=sys.version_info; exit(0 if (v.major,v.minor)>=(3,11) else 1)' 2>/dev/null; then echo 1; exit 0; fi; done; echo 0)
ifneq ($(PYTHON_OK), 1)
$(error Error: This project requires Python >= 3.11.)
endif

help:
	@echo "mcp-ig-extension development commands"
	@echo ""
	@echo "  make install-dev     Install package + dev dependencies (editable)"
	@echo "  make test            Run pytest"
	@echo "  make lint            Run ruff + mypy"
	@echo "  make build-image     Build Docker image for Lambda"
	@echo "  make clean           Remove build artifacts"
	@echo ""
	@echo "  make tf-init         terraform -chdir=terraform init"
	@echo "  make tf-plan         terraform -chdir=terraform plan"
	@echo "  make tf-apply        terraform -chdir=terraform apply (auto-approve)"
	@echo ""
	@echo "  make push-to-ecr     Build + push image with unique tag (updates terraform.tfvars)"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest -q --tb=short

lint:
	ruff check src
	ruff format --check src
	mypy src

build-image:
	@echo "==> Building container image 'mcp-ig-extension:latest' (linux/amd64 for Lambda) ..."
	docker buildx build \
		--platform linux/amd64 \
		--provenance=false \
		--sbom=false \
		-t mcp-ig-extension:latest \
		--load \
		-f Dockerfile .
	@echo "Done. Local image: mcp-ig-extension:latest"

push-to-ecr:
	@set -e; \
	REPO="$(ECR_REPO)"; \
	if [ -z "$$REPO" ]; then \
		ACCT=$$(aws sts get-caller-identity --query Account --output text 2>/dev/null || true); \
		if [ -z "$$ACCT" ]; then \
			echo "Error: ECR_REPO not provided and could not auto-detect AWS account."; \
			echo "Usage: make push-to-ecr ECR_REPO=<acct>.dkr.ecr.us-east-1.amazonaws.com/mcp-ig-extension"; \
			exit 1; \
		fi; \
		REPO="$$ACCT.dkr.ecr.us-east-1.amazonaws.com/mcp-ig-extension"; \
		echo "==> Auto-detected ECR repo: $$REPO"; \
	fi; \
	REGISTRY=$$(echo "$$REPO" | awk -F/ '{print $$1}'); \
	REGION=$$(echo "$$REPO" | sed -nE 's/.*\.ecr\.([a-z0-9-]+)\.amazonaws\.com.*/\1/p'); \
	if [ -z "$$REGION" ]; then REGION="us-east-1"; fi; \
	aws ecr get-login-password --region "$$REGION" | docker login --username AWS --password-stdin "$$REGISTRY" >/dev/null; \
	REPO_NAME=$$(echo "$$REPO" | awk -F/ '{print $$2}'); \
	aws ecr describe-repositories --repository-names "$$REPO_NAME" --region "$$REGION" >/dev/null 2>&1 || \
		aws ecr create-repository --repository-name "$$REPO_NAME" --region "$$REGION" >/dev/null; \
	BUILD_TAG=$$(date +%Y%m%d-%H%M%S); \
	docker buildx build \
		--platform linux/amd64 \
		--provenance=false \
		--sbom=false \
		-t $$REPO:$$BUILD_TAG \
		-t $$REPO:latest \
		--push \
		-f Dockerfile . ; \
	echo "Pushed $$REPO:$$BUILD_TAG"; \
	echo 'lambda_image_uri = "'$$REPO':'$$BUILD_TAG'"' > terraform/terraform.tfvars.partial; \
	echo "Wrote terraform/terraform.tfvars.partial — merge with your mcp_base_url and secret settings."

clean:
	rm -rf build dist .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	-docker rmi mcp-ig-extension:latest 2>/dev/null || true

tf-init:
	terraform -chdir=terraform init

tf-plan:
	terraform -chdir=terraform plan

tf-apply:
	terraform -chdir=terraform apply -auto-approve
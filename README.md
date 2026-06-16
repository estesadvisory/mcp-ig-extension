# mcp-ig-extension

**Scheduled container Lambda that monitors Instagram accounts and writes metrics into your deployed grok-memory-mcp server over authenticated HTTPS.**

This repository is fully independent from [grok-memory-mcp](https://github.com/mikeestes/grok-memory-mcp): own git history, dependencies, Terraform, and container image. It does not import MCP code — only HTTP + boto3.

## Purpose

- Runs on an EventBridge schedule (default: every 6 hours)
- Pulls post, reel, and story metrics via the official Meta Graph API
- Transforms results into dot-notation keys under `ig_monitor.*`
- Writes JSON payloads to your MCP Function URL using a Bearer token from Secrets Manager

See the locked design (2026-06-15) in this repo's planning context for architecture, auth decisions, and roadmap.

## Architecture

```
EventBridge (schedule)
        │
        ▼
IG Extension Lambda (container, Python 3.11)
  ├─ load config/accounts.json
  ├─ Secrets Manager → MCP bearer + IG access tokens
  ├─ Meta Graph API → media + insights
  └─ HTTPS POST → grok-memory-mcp Function URL (store tool)
        │
        ▼
MCP storage (dot-notation keys)
```

Key characteristics:

- **Loose coupling** — MCP is just an HTTPS service
- **Laptop deploy** — `make push-to-ecr` then `cd terraform && terraform apply` (same pattern as grok-memory-mcp)
- **v1 scope** — metrics JSON only; no media download or message archiving

## Repository layout

```
mcp-ig-extension/
├── README.md
├── Dockerfile
├── pyproject.toml
├── Makefile
├── src/
│   └── handler.py              # Lambda entrypoint
├── config/
│   └── accounts.json           # v1 account definitions
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── iam.tf
│   ├── eventbridge.tf
│   ├── lambda.tf
│   ├── ecr.tf
│   └── outputs.tf
├── .github/workflows/          # CI/CD placeholder
└── docs/
    └── key-schema.md
```

## Quick start

### 1. Prerequisites

- Python 3.11+
- Docker with buildx
- AWS CLI configured (`aws sso login` or similar)
- A deployed grok-memory-mcp Function URL
- Secrets in AWS Secrets Manager:
  - `mcp/ig-extension/bearer-token` (or your chosen name) — MCP Bearer token
  - `ig/<account>/access-token` per account in `config/accounts.json`

### 2. Local setup

```bash
cd mcp-ig-extension
python3.11 -m venv .venv && source .venv/bin/activate
make install-dev
```

### 3. Build and push image

```bash
make push-to-ecr
```

This builds for `linux/amd64`, pushes to ECR, and writes `terraform/terraform.tfvars.partial` with the image URI.

### 4. Configure Terraform

Copy and edit variables:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Set lambda_image_uri, mcp_base_url, mcp_auth_secret_name
```

### 5. Deploy

```bash
make tf-init
make tf-plan
make tf-apply
```

### 6. Test manually

```bash
aws lambda invoke \
  --function-name ig-mcp-extension-prod \
  --payload '{}' \
  /tmp/ig-out.json && cat /tmp/ig-out.json
```

## Runtime modes

| Env var | Default | Description |
|---------|---------|-------------|
| `DUMMY_MODE` | `true` | Skip Graph API; emit one dummy write per account |
| `DRY_RUN` | `false` | Log MCP payloads without sending HTTP |
| `MCP_BASE_URL` | (required) | grok-memory-mcp Function URL |
| `MCP_AUTH_SECRET_NAME` | (required) | Secrets Manager name for Bearer token |

Set `dummy_mode = false` in `terraform.tfvars` when IG tokens and Graph API access are ready.

## Authentication (v1)

Hybrid model (design decision 2026-06-15):

- Grok day-to-day usage stays on the official connected grok-memory-mcp
- Your deployed MCP validates `Authorization: Bearer <token>` for external clients like this extension
- IG access tokens also live in Secrets Manager; Lambda IAM allows `ig/*` prefix reads

## Key schema

See [docs/key-schema.md](docs/key-schema.md) for `ig_monitor.*` key patterns and payload shape.

## Open items

1. **MCP POST framing** — Handler uses JSON-RPC `tools/call` → `store` aligned with grok-memory-mcp. Confirm against your deployed MCP once Bearer auth lands there.
2. **First test account** — `config/accounts.json` ships with placeholder `me2dafuture` IDs; replace with real `ig_user_id` and secrets before live runs.
3. **Config location** — v1 uses committed `accounts.json`; can move to MCP or SSM later.

## Development status (roadmap)

- [x] Repo structure + Dockerfile + hello-world handler
- [x] Terraform skeleton (Lambda + EventBridge + IAM + ECR)
- [x] Secrets + dummy MCP POST payload
- [x] Meta Graph client + metrics extraction (behind `DUMMY_MODE=false`)
- [ ] End-to-end test with one live account
- [ ] Error handling hardening + CloudWatch dashboard
- [ ] GitHub Actions deploy pipeline

## Related projects

- [grok-memory-mcp](https://github.com/mikeestes/grok-memory-mcp) — reference deployment pattern (Terraform subdir, container Lambda, ECR workflow). **Do not modify that repo from here.**

## License

MIT
# GitHub App Setup for Local Webhook Testing

This guide supports Phase 5.1: GitHub App registration and local webhook config.

## 1. Create the GitHub App

In GitHub, open:

```text
Settings -> Developer settings -> GitHub Apps -> New GitHub App
```

Use a clear app name such as `PatchProof Local` for local development.

## 2. Set the webhook URL

Start a local tunnel to the backend first. With ngrok, the shape is:

```bash
ngrok http 8000
```

With Cloudflare Tunnel, use the equivalent command that forwards to:

```text
http://localhost:8000
```

Set the GitHub App webhook URL to:

```text
https://<your-tunnel-host>/github/webhook
```

The `/github/webhook` endpoint is implemented in milestone 5.2. Milestone 5.1
only prepares the registration and configuration values.

## 3. Set minimum permissions

Use the smallest permissions needed for PatchProof:

| Permission | Access |
|---|---|
| Contents | Read |
| Pull requests | Read and write |
| Issues | Read |
| Metadata | Read |

Metadata read permission is mandatory for GitHub Apps.

## 4. Subscribe to events

Subscribe to:

```text
pull_request
```

That lets GitHub notify PatchProof when a PR is opened, reopened, edited, or
synchronized.

## 5. Generate and store the private key

After creating the app, generate and download a private key from the GitHub App
settings page. Put it somewhere local and ignored by Git, for example:

```text
./secrets/patchproof-github-app.private-key.pem
```

Private key files are ignored by `.gitignore` using these rules:

```text
*.pem
*.private-key.pem
secrets/
```

Do not commit the `.pem` file.

## 6. Configure local environment variables

Copy `.env.example` to `.env` and fill in:

```bash
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_PATH=./secrets/patchproof-github-app.private-key.pem
GITHUB_WEBHOOK_SECRET=replace-with-a-random-webhook-secret
```

`GITHUB_WEBHOOK_SECRET` must match the webhook secret configured in GitHub's App
settings.

## 7. Install the app on a test repository

After registration, install the GitHub App on a test repository. That repository
is what GitHub will send `pull_request` webhooks for.

## Local Docker Compose behavior

`docker-compose.yml` passes the GitHub App settings through to the backend:

```yaml
GITHUB_APP_ID: ${GITHUB_APP_ID:-}
GITHUB_APP_PRIVATE_KEY_PATH: ${GITHUB_APP_PRIVATE_KEY_PATH:-}
GITHUB_WEBHOOK_SECRET: ${GITHUB_WEBHOOK_SECRET:-}
```

When running with Docker Compose, make sure the private key path points to a path
that exists inside the backend container. Because the repository is mounted at
`/app`, a repo-relative path like this works:

```text
./secrets/patchproof-github-app.private-key.pem
```
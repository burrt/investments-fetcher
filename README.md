# Investments Fetcher

![CICD status](https://github.com/burrt/investments-fetcher/actions/workflows/cicd.yml/badge.svg?branch=main)

Pulls economic data from official sources.

## Getting started

Install [uv](https://docs.astral.sh/uv/) once with `brew install uv`, then:

```bash
git clone https://github.com/burrt/investments-fetcher.git
cd investments-fetcher
uv venv --python 3.12 venv
source venv/bin/activate
uv pip install -r requirements.txt
```

uv downloads Python 3.12 if needed, matching CI. If replacing an older venv,
deactivate it and move it aside before creating the new one.

Configure credentials in `.env` or AWS Parameter Store, then run:

```bash
python fetcher.py
```

Local runs currently send Slack notifications and may upload to S3; dry-run mode
is not yet implemented.

## Updating packages

From the project directory:

```bash
source venv/bin/activate
uv pip compile --upgrade requirements.in -o requirements.txt
uv pip install -r requirements.txt
uv pip check
```

Edit `requirements.in` to add or remove direct dependencies. The commands above
refresh the pinned versions in `requirements.txt` and install them locally.
Review and validate the changes before committing; CI installs these exact pins.

## Deploying to AWS Lambda

Pushes to `main` deploy automatically through [GitHub Actions](.github/workflows/cicd.yml).
The workflow authenticates with AWS using OIDC, builds the ZIP with
`prepare-deploy.sh`, and tags the Lambda function with the deployed commit hash.

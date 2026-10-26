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

uv downloads Python 3.12 if needed. Move any older venv aside first.

For local runs, put the provider's API key (e.g. `BEA_API_KEY`) and Slack webhooks
in `.env`. Both webhook variables can be set:

* `--dry-run`: uses `SLACK_TESTING_WEBHOOK_URL`; skips S3 and Parameter Store.
* Normal runs: use `SLACK_WEBHOOK_URL`, falling back to Parameter Store for missing
  credentials. S3 uploads require `SKIP_S3_UPLOAD=false`.

Lambda uses environment variables and Parameter Store, without loading `.env`.
See commands and examples:

```bash
python fetcher.py --help
```

Run tests (no network or credentials needed):

```bash
python -m unittest discover -s tests
```

## Updating packages

From the project directory:

```bash
source venv/bin/activate
uv pip compile --upgrade requirements.in -o requirements.txt
uv pip install -r requirements.txt
uv pip check
```

Edit `requirements.in` to add or remove dependencies. Review and validate the
updated `requirements.txt` before committing; CI installs those exact versions.

## Deploying to AWS Lambda

Pushes to `main` deploy automatically through [GitHub Actions](.github/workflows/cicd.yml)
using `prepare-deploy.sh`. The Lambda function is tagged with the deployed commit.

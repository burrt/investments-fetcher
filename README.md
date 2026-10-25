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

Set the provider's API key (e.g. `BEA_API_KEY`) and `SLACK_TESTING_WEBHOOK_URL`
in `.env`. See options and examples:

```bash
python fetcher.py --help
```

`--dry-run` fetches real data and posts to testing Slack. It skips S3 and Parameter
Store; missing credentials cause an error.

Without `--dry-run`, runs use `SLACK_WEBHOOK_URL` (or AWS Parameter Store) and upload
to S3 only when `SKIP_S3_UPLOAD=false`.

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

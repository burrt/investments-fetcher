# Investments Fetcher

![CICD status](https://github.com/burrt/investments-fetcher/actions/workflows/cicd.yml/badge.svg?branch=main)

Pulls economic data from official sources.

## Getting started

```bash
# clone the repo
$ git clone https://github.com/burrt/investments-fetcher.git

# install venv if it's not already installed
$~/investments-fetcher python3 -m venv venv
$~/investments-fetcher source venv/bin/activate

# use pip-tools
$ python -m pip install pip-tools
$ pip-compile requirements.in

# install packages
$ pip install -r requirements.txt

# running
$ python fetcher.py
```

## Deploying to AWS Lambda

* the deployment package is created with the `prepare-deploy.sh`
* using GitHub Actions for full deployment - see `cicd.yml`
* OIDC is setup with GitHub and AWS with the role authorized to update the Lambda
* AWS Lambda function is tagged with the latest commit hash

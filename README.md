# Investment watcher

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

```bash
# setup virtual env
$~/investments-fetcher$ python3.12 -m venv venv
$~/investments-fetcher source ./venv/bin/activate

# use pip-tools
$ python -m pip install pip-tools
$ pip-compile requirements.in

# install packages to /package
$ mkdir package

$ pip install -r requirements.txt --target ./package

# zip python venv
$~/investments-fetcher deactivate
$~/investments-fetcher cd venv/lib/python3.12/site-packages
$~/investments-fetcher/venv/lib/python3.12/site-packages$ zip -r ../../../../deployment_package.zip .

# zip installed packages into the deployment blob
$ cd ../../../../
$ cd package
$ zip -r ../deployment_package.zip .
$ cd ..

# zip any modules
$ zip -r deployment_package.zip aws
$ zip -r deployment_package.zip data_source
$ zip -r deployment_package.zip logger

$ zip deployment_package.zip fetcher.py

$ aws lambda create-function --function-name investments-fetcher \
--runtime python3.12 --handler fetcher.lambda_handler \
--role arn:aws:iam::398018169858:role/investments-fetcher-lambda-role \
--zip-file fileb://deployment_package.zip

$ aws lambda update-function-code --function-name investments-fetcher --zip-file fileb://deployment_package.zip

```

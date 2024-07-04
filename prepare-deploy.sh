zip deployment_package.zip

cd venv/lib/python3.12/site-packages
zip -r ../../../../deployment_package.zip . -x "*/__pycache__/*"

# zip installed packages into the deployment blob
cd ../../../../
cd package
zip -r ../deployment_package.zip . -x "*/__pycache__/*"
cd ..

# zip any modules
zip -r deployment_package.zip aws -x "*/__pycache__/*"
zip -r deployment_package.zip data_source -x "*/__pycache__/*"
zip -r deployment_package.zip logger -x "*/__pycache__/*"

zip deployment_package.zip fetcher.py -x "*/__pycache__/*"

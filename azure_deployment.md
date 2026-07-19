# Azure Production Deployment Guide

This guide details the steps to build your container, push it to Azure Container Registry (ACR), and deploy it to Azure Container Apps (ACA) or Azure App Service.

## Prerequisites
- Docker Desktop installed and running on your deployment system.
- Azure CLI (`az`) installed: [Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli).
- Azure subscription with permissions to create resources.

---

## Step 1: Login to Azure and Setup Resources

1. Log in to your Azure account:
   ```bash
   az login
   ```
2. Create a Resource Group:
   ```bash
   az group create --name tg-loan-processing --location eastus
   ```
3. Create an Azure Container Registry (ACR) to store your Docker image:
   ```bash
   az acr create --resource-group tg-loan-processing --name loanprocessingacr --sku Basic
   ```
4. Log in to the registry:
   ```bash
   az acr login --name loanprocessingacr
   ```

---

## Step 2: Build and Push the Docker Image

1. Build the Docker image locally (from your repository root):
   ```bash
   docker build -t loanprocessingacr.azurecr.io/loan-processing-crew:latest .
   ```
2. Push the image to your Azure Container Registry:
   ```bash
   docker push loanprocessingacr.azurecr.io/loan-processing-crew:latest
   ```

---

## Step 3: Deployment Options in Azure

### Option A: Azure Container Apps (Recommended)
Azure Container Apps (ACA) is the ideal serverless container platform for multi-agent applications, providing automatic scaling, secrets management, and easy configuration.

1. Enable ACR Admin user to allow ACA to pull the image:
   ```bash
   az acr update --n loanprocessingacr --admin-enabled true
   ```
2. Get the ACR password:
   ```bash
   az acr credential show --name loanprocessingacr --query "passwords[0].value"
   ```
3. Deploy to Azure Container Apps:
   ```bash
   az containerapp create \
     --name loan-processing-dashboard \
     --resource-group tg-loan-processing \
     --image loanprocessingacr.azurecr.io/loan-processing-crew:latest \
     --target-port 8501 \
     --ingress external \
     --query-port 8501 \
     --env-vars \
       OPENAI_API_KEY="<your-openai-api-key>" \
       ARIZE_API_KEY="<your-arize-api-key>" \
       ARIZE_SPACE_ID="<your-arize-space-id>" \
       ARIZE_PROJECT_NAME="LOANAGENTS"
   ```

---

### Option B: Azure App Service
If you prefer a managed web hosting model, you can deploy to Azure App Service (Web App for Containers).

1. Create an App Service Plan (Linux):
   ```bash
   az appservice plan create --name plan-loan-processing --resource-group tg-loan-processing --sku B1 --is-linux
   ```
2. Create the Web App:
   ```bash
   az webapp create \
     --name loan-processing-app \
     --resource-group tg-loan-processing \
     --plan plan-loan-processing \
     --container-image-name loanprocessingacr.azurecr.io/loan-processing-crew:latest
   ```
3. Configure the app to use port `8501`:
   ```bash
   az webapp config appsettings set --name loan-processing-app --resource-group tg-loan-processing --settings WEBSITES_PORT=8501
   ```
4. Set env secrets under **Settings > Configuration > Application settings** on the Azure Portal.

---

## Step 4: Storage Persistence (Critical for Production)

Because Streamlit writes decision reports and SQLite databases locally inside `/app/output`, restarting the container will wipe out previous decisions. 

To persist these files:
1. **Create an Azure File Share** in a Storage Account.
2. In the Azure Portal for your App Service or Container App:
   - Navigate to **Configuration > Path mappings** (App Service) or **Volumes** (Container Apps).
   - Mount your Azure File Share to the path `/app/output`.
3. This guarantees that `telemetry.db`, `phoenix_evals.db`, and decision reports are safely saved outside the container and remain intact across updates or restarts.

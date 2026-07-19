# Deploying to Azure Container Apps via the Azure Portal

This guide provides step-by-step instructions for creating your Azure Container Registry (ACR) and deploying your containerized app to **Azure Container Apps** entirely through the **Azure Portal Web UI**.

---

## Step 1: Create the Azure Container Registry (ACR)
First, you need a registry in Azure to host your Docker image.

1. Open the [Azure Portal](https://portal.azure.com).
2. In the search bar at the top, type `Container registries` and select it.
3. Click **+ Create** in the top left:
   - **Resource group**: Select or create a new one (e.g. `tg-loan-processing`).
   - **Registry name**: Type a unique name (e.g. `loanregistry1`). It must be 5-50 alphanumeric characters.
   - **Location**: Choose a region near you (e.g., `East US`).
   - **SKU**: Select **Basic** (cheaper for testing/production start).
4. Click **Review + create**, then click **Create**.
5. Once deployment is complete, click **Go to resource**.
6. In the left sidebar, under **Settings**, click on **Access keys**.
7. Enable the **Admin user** toggle (this generates a password so Azure Container Apps can easily pull your image).

---

## Step 2: Build & Push the Image to ACR (Required CLI Step)
While deployment is done via the portal, pushing your local code to your Azure registry requires a terminal/command prompt:

1. Open your terminal in your project directory (`d:\AI-Workspace\BFSI\crewai\loan_processing_crew`).
2. Log in to your Azure account:
   ```bash
   az login
   ```
3. Log in to your ACR registry:
   ```bash
   az acr login --name loanregistry1
   ```
4. Build your Docker image locally and tag it for your ACR:
   ```bash
   docker build -t loanregistry1.azurecr.io/loan-processing-crew:latest .
   ```
5. Push the image to the cloud registry:
   ```bash
   docker push loanregistry1.azurecr.io/loan-processing-crew:latest
   ```

---

## Step 3: Create the Azure Container App from the Portal
Now, deploy the running app inside Azure.

1. In the Azure Portal search bar, type `Container Apps` and select it.
2. Click **+ Create** in the top left.
3. Fill in the **Basics** tab:
   - **Project Details**: Select your subscription and Resource Group.
   - **Container app name**: Enter a name (e.g., `loan-processing-dashboard`).
   - **Deployment source**: Select **Container image**.
4. Move to the **Container** tab:
   - Uncheck **Use simple starter image**.
   - Under **Image source**, select **Azure Container Registry**.
   - **Registry**: Select your registry (`loanregistry1`).
   - **Image**: Select `loan-processing-crew`.
   - **Tag**: Select `latest`.
   - **CPU and Memory**: Select `0.5 cores` and `1.0 Gi` (sufficient for CrewAI dashboard).
5. Move to the **Ingress** tab:
   - **Ingress**: Select **Enabled**.
   - **Ingress type**: Select **HTTP**.
   - **Client certificate mode**: Select **Ignore**.
   - **Target port**: Type `8501` (this is the port exposed in our Dockerfile).
   - **Traffic**: Select **Accepting traffic from anywhere (External)**.
6. Click **Review + create**, then click **Create**. Wait 2-3 minutes for the app to spin up.
7. Click **Go to resource** when deployment finishes.

---

## Step 4: Configure Secrets & Environment Variables

To allow the container to connect to OpenAI and Arize AX:

1. Go to your **Container App** page in the Azure Portal.
2. In the left sidebar under the **Settings** section, click on **Secrets**.
3. Click **+ Add** to add your secret keys securely:
   - Add name `openai-key` with your value: `sk-proj-...`
   - Add name `arize-key` with your value: `ak-90f3...`
   - Click **Save**.
4. In the left sidebar under the **Application** section, click on **Containers**.
5. Click the **Edit and deploy** button at the top:
   - Click on your container name in the list.
   - Under **Environment variables**, click **+ Add** to map your configuration:
     - Name: `OPENAI_API_KEY` | Source: `Secret reference` | Value: `openai-key`
     - Name: `ARIZE_API_KEY` | Source: `Secret reference` | Value: `arize-key`
     - Name: `ARIZE_SPACE_ID` | Source: `Manual entry` | Value: `U3BhY2U6Mzk3NTg6M1l3dg==`
     - Name: `ARIZE_PROJECT_NAME` | Source: `Manual entry` | Value: `LOANAGENTS`
6. Click **Save** at the bottom, then click **Create** to deploy the changes.

---

## Step 5: Open Your Dashboard

1. Once the revision is successfully deployed, go to the **Overview** page of your Container App.
2. Look for the **Application Url** (in the top right section).
3. Click the link (it will look like `https://loan-processing-dashboard.<unique-id>.eastus.azurecontainerapps.io`).
4. Your Streamlit dashboard is now live and running in the cloud!

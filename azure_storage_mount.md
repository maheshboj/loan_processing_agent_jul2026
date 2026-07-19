# Step-by-Step Azure File Share Setup & Mount Guide

This beginner-friendly guide walks you through setting up an Azure Storage Account, creating a File Share, and mounting it to your containerized app so that your SQLite databases and loan decision markdown files are safely persisted.

You can perform these steps using either the **Azure Portal (Web UI)** or the **Azure CLI (Command Line)**. Both methods are detailed below.

---

## Method 1: Using the Azure Portal (Web Web Interface)

### Part A: Create a Storage Account
1. Log in to the [Azure Portal](https://portal.azure.com).
2. In the search bar at the top, type `Storage accounts` and click on it under Services.
3. Click the **+ Create** button in the top left.
4. Fill in the **Basics** tab:
   - **Subscription**: Select your active Azure subscription.
   - **Resource Group**: Select the resource group you created earlier (e.g., `tg-loan-processing`), or click *Create new* and name it.
   - **Storage account name**: Type a unique, lowercase name with no spaces or symbols (e.g., `loanprocessingstorage1`).
   - **Region**: Choose the same region as your container (e.g., `East US`).
   - **Performance**: Select **Standard** (recommended for general use).
   - **Redundancy**: Select **LRS (Locally-redundant storage)** to minimize costs for development/production testing.
5. Click **Review + create** at the bottom, then click **Create**. Wait 1–2 minutes for the deployment to finish, then click **Go to resource**.

### Part B: Create the File Share
1. Inside your Storage Account page, look at the left sidebar menu.
2. Under the **Data storage** section, click on **File shares**.
3. Click the **+ File share** button at the top.
4. In the pane that opens:
   - **Name**: Type a lowercase name (e.g., `app-output`).
   - **Tier**: Select **Transaction optimized** or **Hot**.
5. Click **Create**. Your new file share will now appear in the list.

### Part C: Get Storage Access Keys
1. In the left sidebar of your Storage Account, scroll down to the **Security + networking** section.
2. Click on **Access keys**.
3. You will see `key1` and `key2`. Click **Show** next to the **Key** field under `key1`, and copy it. (Keep this key private).
4. Save your **Storage account name** and this **Access Key** for the next step.

---

## Method 2: Using the Azure CLI (Terminal)

If you prefer the command line, run these commands in your terminal after logging in via `az login`:

1. **Create the Storage Account**:
   ```bash
   az storage account create \
     --name loanprocessingstorage1 \
     --resource-group tg-loan-processing \
     --location eastus \
     --sku Standard_LRS \
     --kind StorageV2
   ```
2. **Create the File Share**:
   ```bash
   az storage share create \
     --name app-output \
     --account-name loanprocessingstorage1
   ```
3. **Get the Storage Access Key**:
   ```bash
   az storage account keys list \
     --account-name loanprocessingstorage1 \
     --resource-group tg-loan-processing \
     --query "[0].value" \
     --output tsv
   ```

---

## Step 4: Mount the File Share to Your Container

Now that your File Share is ready, mount it to your Azure Container so it replaces `/app/output`.

### Option A: If using Azure Container Apps (ACA)
1. Go to your **Container App** in the Azure Portal.
2. In the left sidebar, click **Settings > Storage** (under the Application section).
3. Click **+ Add** to define a Storage Link:
   - **Name**: Type `loan-storage-mount`.
   - **Storage account name**: `loanprocessingstorage1`.
   - **Access Key**: Paste the key you copied in Part C.
   - Click **Save**.
4. Now, go to **Settings > Containers** in the left sidebar.
5. Select your container, click **Edit and deploy** at the top:
   - Go to the **Volumes** tab and click **+ Add**:
     - **Volume name**: `output-volume`.
     - **Volume type**: `Azure file`.
     - **Select storage**: Choose `loan-storage-mount` (created in Step 3).
     - **File share name**: `app-output`.
   - Go to the **Volume mounts** tab under your container setup:
     - **Volume**: `output-volume`.
     - **Mount path**: `/app/output`.
6. Click **Create** to deploy a new revision. Your application will restart and write all reports and SQLite databases to the Azure File Share.

---

### Option B: If using Azure App Service
1. Go to your **App Service** in the Azure Portal.
2. In the left sidebar, click **Settings > Configuration** (or **Settings > Environment variables** in newer portals).
3. Click on the **Path mappings** tab.
4. Click **+ New Azure Storage Mount**:
   - **Name**: `output-mount`.
   - **Configuration Options**: Select **Basic**.
   - **Storage Account**: Select your account (`loanprocessingstorage1`).
   - **Storage Container/Share**: Select your share (`app-output`).
   - **Mount Path**: `/app/output`.
5. Click **OK**, then click **Save** at the top of the Configuration page and confirm.
6. The app service will restart automatically and mount the directory.

# 🚀 Deployment Guide — Lost & Found AI

---

## Option A — Streamlit Cloud (Easiest, Free)

### Step 1 — Push your code to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/lost-found-ai.git
git push -u origin main
```

### Step 2 — Add Secrets on Streamlit Cloud
1. Go to https://share.streamlit.io
2. Click **New app** → select your repo → set `app.py` as the main file
3. Click **Advanced settings → Secrets** and paste:

```toml
CLOUDINARY_CLOUD_NAME = "your_cloud_name"
CLOUDINARY_API_KEY    = "your_api_key"
CLOUDINARY_API_SECRET = "your_api_secret"
DB_PATH               = "lost_found.db"
```

4. Click **Deploy** — done! ✅

> ⚠️ Note: Streamlit Cloud resets the local SQLite DB on each redeploy.
> For persistent data, replace SQLite with a free hosted DB like
> [Supabase](https://supabase.com) or [PlanetScale](https://planetscale.com).

---

## Option B — Microsoft Azure Container App

### Prerequisites
- Azure CLI installed: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
- Docker installed: https://www.docker.com/get-started
- An Azure account

---

### Step 1 — Login to Azure
```bash
az login
```

### Step 2 — Set variables
```bash
RESOURCE_GROUP="lost-found-rg"
LOCATION="eastus"
ACR_NAME="lostfoundacr"          # must be globally unique, lowercase
APP_NAME="lost-found-app"
CONTAINER_ENV="lost-found-env"
IMAGE_NAME="lost-found-ai"
```

### Step 3 — Create Resource Group
```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### Step 4 — Create Azure Container Registry (ACR)
```bash
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true
```

### Step 5 — Build & Push Docker image to ACR
```bash
# Login to ACR
az acr login --name $ACR_NAME

# Build image
docker build -t $IMAGE_NAME .

# Tag for ACR
docker tag $IMAGE_NAME $ACR_NAME.azurecr.io/$IMAGE_NAME:latest

# Push
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:latest
```

### Step 6 — Get ACR credentials
```bash
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
```

### Step 7 — Create Container Apps Environment
```bash
az containerapp env create \
  --name $CONTAINER_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 8 — Deploy the Container App
```bash
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $ACR_NAME.azurecr.io/$IMAGE_NAME:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_NAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8501 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --env-vars \
    CLOUDINARY_CLOUD_NAME=your_cloud_name \
    CLOUDINARY_API_KEY=your_api_key \
    CLOUDINARY_API_SECRET=your_api_secret \
    DB_PATH=/tmp/lost_found.db
```

### Step 9 — Get your live URL
```bash
az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.configuration.ingress.fqdn" -o tsv
```
Your app is now live at `https://<fqdn>` ✅

---

### Step 10 (Optional) — Update after code changes
```bash
docker build -t $IMAGE_NAME .
docker tag $IMAGE_NAME $ACR_NAME.azurecr.io/$IMAGE_NAME:latest
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:latest

az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/$IMAGE_NAME:latest
```

---

## 💡 Production Tips

| Concern | Solution |
|---|---|
| Persistent DB on Azure | Use [Azure Database for PostgreSQL](https://azure.microsoft.com/en-us/products/postgresql) and swap SQLite calls |
| Free persistent DB | [Supabase](https://supabase.com) (free tier, Postgres) |
| Image hosting | Cloudinary (already configured) |
| Secrets management | Azure Key Vault or Streamlit secrets |
| Custom domain | Azure Container App → Custom Domain settings |

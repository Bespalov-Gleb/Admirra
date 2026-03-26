#!/bin/bash
set -e

FRONTEND_BUILD_CONTEXT="./admin-panel-vue-main/admin-panel-vue-main"
DEPLOY_DIR="/var/www/admirra.online"
BACKUP_DIR="/var/www/admirra.online.backup.$(date +%Y%m%d_%H%M%S)"
DOCKER_IMAGE_NAME="temp-frontend-builder"
DOCKER_CONTAINER_NAME="temp-frontend-extractor"

echo "=================================================="
echo "🚀 FRONTEND DEPLOYMENT SCRIPT (Docker-based)"
echo "=================================================="

# 1. Build frontend Docker image
echo ""
echo "🐳 Step 1: Building frontend Docker image: $DOCKER_IMAGE_NAME"
docker build -t "$DOCKER_IMAGE_NAME" "$FRONTEND_BUILD_CONTEXT"

# 2. Create a temporary container to extract build artifacts
echo ""
echo "📦 Step 2: Creating temporary container to extract build artifacts..."
docker create --name "$DOCKER_CONTAINER_NAME" "$DOCKER_IMAGE_NAME"

# 3. Extract files from the temporary container
echo ""
echo "📤 Step 3: Extracting built files to /tmp/new-frontend..."
sudo rm -rf /tmp/new-frontend # Clean up previous temp dir if any
docker cp "$DOCKER_CONTAINER_NAME":/usr/share/nginx/html /tmp/new-frontend

# 4. Remove the temporary container
echo ""
echo "🗑️  Step 4: Removing temporary container..."
docker rm "$DOCKER_CONTAINER_NAME"

# 5. Remove the temporary Docker image
echo ""
echo "🗑️  Step 5: Removing temporary Docker image..."
docker rmi "$DOCKER_IMAGE_NAME"

# 6. Create backup of old frontend
if [ -d "$DEPLOY_DIR" ]; then
    echo ""
    echo "💾 Step 6: Creating backup of existing frontend to $BACKUP_DIR"
    sudo mv "$DEPLOY_DIR" "$BACKUP_DIR"
else
    echo ""
    echo "ℹ️  Step 6: No existing frontend found at $DEPLOY_DIR. Skipping backup."
fi

# 7. Copy new build files
echo ""
echo "📋 Step 7: Copying new frontend files from /tmp/new-frontend to $DEPLOY_DIR"
sudo mkdir -p "$DEPLOY_DIR"
sudo cp -r /tmp/new-frontend/* "$DEPLOY_DIR/"

# 8. Set correct permissions
echo ""
echo "🔐 Step 8: Setting permissions for $DEPLOY_DIR"
sudo chown -R www-data:www-data "$DEPLOY_DIR"
sudo chmod -R 755 "$DEPLOY_DIR"

# 9. Verify critical files exist
echo ""
echo "🔍 Step 9: Verifying deployment..."
if [ -f "$DEPLOY_DIR/index.html" ]; then
    echo "✅ index.html found"
else
    echo "❌ ERROR: index.html NOT found! Deployment may have failed."
    exit 1
fi

# 10. Check Nginx config and reload
echo ""
echo "🔧 Step 10: Checking Nginx configuration..."
sudo nginx -t
if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
    echo ""
    echo "🔄 Reloading Nginx..."
    sudo systemctl reload nginx
    echo "✅ Nginx reloaded successfully"
else
    echo "❌ ERROR: Nginx configuration is invalid!"
    exit 1
fi

# 11. Clean up temporary extracted files
echo ""
echo "🧹 Step 11: Cleaning up temporary extracted files..."
sudo rm -rf /tmp/new-frontend

echo ""
echo "=================================================="
echo "✅ FRONTEND DEPLOYMENT COMPLETE!"
echo "=================================================="
echo ""
echo "⚠️  IMPORTANT: Clear your browser cache (Ctrl+Shift+R) to see changes."
echo ""
echo "📊 Deployment Summary:"
echo "   - Frontend built using Docker from: $FRONTEND_BUILD_CONTEXT"
echo "   - Deployed to: $DEPLOY_DIR"
if [ -d "$BACKUP_DIR" ]; then
    echo "   - Backup saved at: $BACKUP_DIR"
fi
echo ""

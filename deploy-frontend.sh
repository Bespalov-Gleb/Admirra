#!/bin/bash
set -e

FRONTEND_DIR="./admin-panel-vue-main/admin-panel-vue-main"
DEPLOY_DIR="/var/www/admirra.ru"
BACKUP_DIR="/var/www/admirra.ru.backup.$(date +%Y%m%d_%H%M%S)"

echo "=================================================="
echo "🚀 FRONTEND DEPLOYMENT SCRIPT"
echo "=================================================="

# 1. Check for Node.js and npm
echo ""
echo "📦 Step 1: Checking Node.js and npm..."
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "❌ Node.js or npm is not installed. Attempting to install..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo "✅ Node.js and npm installed."
else
    echo "✅ Node.js $(node --version) and npm $(npm --version) found."
fi

# 2. Navigate to frontend directory
echo ""
echo "📁 Step 2: Navigating to frontend directory: $FRONTEND_DIR"
cd "$FRONTEND_DIR"

# 3. Install dependencies
echo ""
echo "📥 Step 3: Installing npm dependencies..."
npm install

# 4. Build production frontend
echo ""
echo "🔨 Step 4: Building frontend for production..."
npm run build

# 5. Navigate back to project root
echo ""
echo "📁 Step 5: Navigating back to project root..."
cd -

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
echo "📋 Step 7: Copying new frontend files to $DEPLOY_DIR"
sudo mkdir -p "$DEPLOY_DIR"
sudo cp -r "$FRONTEND_DIR/dist/"* "$DEPLOY_DIR/"

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

echo ""
echo "=================================================="
echo "✅ FRONTEND DEPLOYMENT COMPLETE!"
echo "=================================================="
echo ""
echo "⚠️  IMPORTANT: Clear your browser cache (Ctrl+Shift+R) to see changes."
echo ""
echo "📊 Deployment Summary:"
echo "   - Frontend built from: $FRONTEND_DIR"
echo "   - Deployed to: $DEPLOY_DIR"
if [ -d "$BACKUP_DIR" ]; then
    echo "   - Backup saved at: $BACKUP_DIR"
fi
echo ""


#!/bin/bash

# Latency Monitor - Cloud Foundry Deployment Script

set -e

echo "================================================"
echo "  Latency Monitor - Cloud Foundry Deployment"
echo "================================================"
echo ""

# Check if CF CLI is installed
if ! command -v cf &> /dev/null; then
    echo "❌ Cloud Foundry CLI not found. Please install it first."
    echo "   Visit: https://docs.cloudfoundry.org/cf-cli/install-go-cli.html"
    exit 1
fi

echo "✅ Cloud Foundry CLI found"

# Check if logged in
if ! cf target &> /dev/null; then
    echo "❌ Not logged in to Cloud Foundry"
    echo ""
    echo "Please login first with:"
    echo "  cf login -a <api-endpoint>"
    exit 1
fi

echo "✅ Logged in to Cloud Foundry"
echo ""

# Show current target
echo "Current target:"
cf target
echo ""

# Ask for confirmation
read -p "Deploy to this space? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo "🚀 Deploying latency-monitor..."
echo ""

# Push the app
cf push

echo ""
echo "✅ Deployment complete!"
echo ""

# Get app info
APP_URL=$(cf app latency-monitor | grep -i routes: | awk '{print $2}')

echo "================================================"
echo "  Application deployed successfully!"
echo "================================================"
echo ""
echo "📊 Dashboard: https://${APP_URL}"
echo "🔌 API:       https://${APP_URL}/api/latency"
echo "🏥 Health:    https://${APP_URL}/health"
echo ""
echo "Useful commands:"
echo "  cf logs latency-monitor          # View logs"
echo "  cf app latency-monitor           # App info"
echo "  cf restage latency-monitor       # Restage app"
echo "  cf set-env latency-monitor ...   # Set env var"
echo ""

#!/bin/bash

# Test the WhatsApp Automation System
# Sends a test message via the API to simulate WhatsApp

set -e

API_URL="${1:-http://localhost:8000}"

echo "🧪 Testing WhatsApp Automation API at $API_URL"
echo ""

# Test 1: Health check
echo "1️⃣ Health check..."
curl -s "$API_URL/" | python3 -m json.tool
echo ""

# Test 2: Create a manual task
echo "2️⃣ Creating a test task..."
curl -s -X POST "$API_URL/tasks/create" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "copy_change",
    "description": "Change the hero button text to Get Started Free",
    "scope": ["app/components/Hero.tsx"],
    "rules": ["Do not change layout", "Do not touch styles"],
    "auto_commit": true
  }' | python3 -m json.tool
echo ""

# Test 3: List tasks
echo "3️⃣ Listing all tasks..."
curl -s "$API_URL/tasks" | python3 -m json.tool
echo ""

# Test 4: List messages
echo "4️⃣ Listing messages..."
curl -s "$API_URL/messages" | python3 -m json.tool
echo ""

echo "✅ Tests completed!"
echo ""
echo "💡 To test WhatsApp webhook, use ngrok:"
echo "   ngrok http 8000"
echo "   Then configure the ngrok URL in Twilio Console"

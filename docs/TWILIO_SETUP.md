# Twilio WhatsApp Setup Guide

## 1. Create Twilio Account

1. Go to [Twilio Console](https://console.twilio.com/)
2. Sign up or log in
3. Note your **Account SID** and **Auth Token**

## 2. Enable WhatsApp Sandbox

1. In Twilio Console, go to **Messaging** → **Try it out** → **Send a WhatsApp message**
2. Follow the instructions to join the sandbox:
   - Send "join <your-sandbox-code>" to the WhatsApp number shown
3. Note the sandbox phone number (usually +14155238886)

## 3. Configure Webhook

### Using ngrok (Local Development)

1. Install ngrok: `brew install ngrok`
2. Start your backend: `./start-backend.sh`
3. In another terminal: `ngrok http 8000`
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### Set Webhook in Twilio

1. Go to **Messaging** → **Try it out** → **Send a WhatsApp message**
2. Scroll to "Sandbox Configuration"
3. Set the webhook URL:
   - **When a message comes in**: `https://your-ngrok-url.ngrok.io/webhook/whatsapp`
   - **HTTP Method**: POST

## 4. Test the Integration

1. Send a WhatsApp message to the sandbox number
2. Example messages to try:
   - "Change the hero button to say Book a Free Audit"
   - "Update the page title to Premium Marketing Services"
   - "Change the CTA color to blue"

## 5. Environment Variables

Update your `backend/.env` file:

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

TASKS_DIR=../tasks
```

## 6. Production Setup

For production, use Twilio's WhatsApp Business API:

1. Apply for WhatsApp Business API access
2. Get a dedicated phone number
3. Set up message templates for notifications
4. Use a production webhook URL (not ngrok)

## Troubleshooting

### Messages not arriving
- Check ngrok is running and URL is correct
- Verify webhook URL in Twilio console
- Check Twilio debugger for errors

### Voice notes not transcribing
- Ensure OPENAI_API_KEY is set
- Check Twilio auth credentials for media download

### Intent not parsed correctly
- Try being more specific in your message
- Include the file or component name
- Example: "In the Hero component, change the button text to 'Get Started'"

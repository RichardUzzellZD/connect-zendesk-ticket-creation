# Amazon Connect to Zendesk Ticket Creation

An AWS Lambda function that creates beautifully formatted Zendesk tickets from Amazon Connect call flows with AI agent summaries, sentiment analysis, and automatic high-priority alert detection.

![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-orange.svg)
![Amazon Connect](https://img.shields.io/badge/Amazon-Connect-blue.svg)
![Zendesk](https://img.shields.io/badge/Zendesk-API-green.svg)
![Python](https://img.shields.io/badge/Python-3.12-green.svg)

## Overview

This Lambda function integrates Amazon Connect with Zendesk to automatically create support tickets during or after customer calls. It captures contact flow data, AI agent conversation summaries, customer sentiment, and intent, formatting them into professional HTML tickets with visual styling and priority-based routing.

**Key Feature**: Returns `zendesk_ticket_id` to Amazon Connect, enabling screen pop routing to the specific ticket when agents answer the call.

## Features

✅ **Rich HTML Ticket Formatting**
- Professional styling with color-coded sections
- Call details, customer information, and AI summaries
- Sentiment indicators with emoji badges
- Customer intent tracking

✅ **High-Priority Alert Detection**
- Automatic detection of urgent keywords (fraud, hardship, lost/stolen cards)
- Visual alert banners for critical tickets
- Priority escalation for immediate attention

✅ **AI Agent Integration**
- Captures AI conversation summaries
- Sentiment analysis display (positive, neutral, negative)
- Customer intent classification
- Pre-call intelligence for agents

✅ **Ticket ID Return for Screen Pop**
- Returns `ticket_id` to Connect contact attributes
- Enables routing to open ticket in Zendesk
- Provides context before agent answers call

✅ **Flexible Configuration**
- Custom fields support
- Tag management
- Priority and type customization
- Requester auto-creation

## Architecture

```
┌─────────────────────────┐
│   Customer Call         │
│   Phone: +44xxxxxxx     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Amazon Connect        │
│   Contact Flow          │
│   + AI Agent (optional) │
│                         │
│   Collects:             │
│   - Customer data       │
│   - AI summary          │
│   - Sentiment           │
│   - Intent              │
└───────────┬─────────────┘
            │
            │ Invoke Lambda with parameters
            ▼
┌─────────────────────────┐
│   Lambda Function       │
│   createZendeskTicket   │
│                         │
│   1. Extract parameters │
│   2. Build HTML ticket  │
│   3. Detect priority    │
│   4. Call Zendesk API   │
│   5. Return ticket ID   │
└───────────┬─────────────┘
            │
            │ POST /api/v2/tickets.json
            ▼
┌─────────────────────────┐
│      Zendesk            │
│                         │
│   Creates ticket with:  │
│   - Formatted HTML      │
│   - Tags                │
│   - Priority            │
│   - Custom fields       │
│                         │
│   Returns: ticket_id    │
└───────────┬─────────────┘
            │
            │ ticket_id returned
            ▼
┌─────────────────────────┐
│   Amazon Connect        │
│                         │
│   Sets contact attribute│
│   zendesk_ticket_id     │
│                         │
│   Agent screen pop      │
│   routes to ticket      │
└─────────────────────────┘
```

## Data Flow

### Input (from Amazon Connect)

```json
{
  "Details": {
    "ContactData": {
      "ContactId": "abc-123-def",
      "CustomerEndpoint": {"Address": "+447425162654"},
      "Queue": {"Name": "Support Queue"},
      "InitiationMethod": "INBOUND"
    },
    "Parameters": {
      "customer_name": "Richard Uzzell",
      "customer_email": "richard.uzzell@example.com",
      "customer_number": "MEM12345",
      "subject": "Customer inquiry",
      "summary": "Customer called about payment arrangement...",
      "sentiment": "negative",
      "customerIntent": "payment_arrangement",
      "priority": "high",
      "tags": "amazon_connect,ai_agent,payment"
    }
  }
}
```

### Output (to Amazon Connect)

```json
{
  "success": "true",
  "ticket_id": "12345",
  "ticket_url": "https://company.zendesk.com/agent/tickets/12345",
  "contact_id": "abc-123-def"
}
```

### Usage in Contact Flow

**After Lambda invocation, set contact attribute:**
- Attribute: `zendesk_ticket_id`
- Value: `$.External.ticket_id`

**Then route call to queue:**
- Agent's Zendesk screen pops to ticket #12345
- Agent has full context before answering

## Installation

See [INSTALLATION.md](INSTALLATION.md) for complete setup instructions.

### Quick Start

1. Create Lambda function with code from `lambda_function.py`
2. Set environment variables (Zendesk subdomain, email, API token)
3. Add `requests` library via Lambda Layer
4. Grant Amazon Connect permission to invoke Lambda
5. Add Lambda to Connect instance
6. Use "Invoke AWS Lambda function" in contact flow
7. Store returned `ticket_id` in contact attributes

## Configuration

### Environment Variables (Required)

| Variable | Description | Example |
|----------|-------------|---------|
| `ZENDESK_SUBDOMAIN` | Your Zendesk subdomain | `mycompany` |
| `ZENDESK_EMAIL` | Zendesk admin email | `admin@mycompany.com` |
| `ZENDESK_API_TOKEN` | Zendesk API token | `abc123...` |

### Contact Flow Parameters (Optional)

All parameters are passed via contact attributes to Lambda:

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `customer_name` | Customer's full name | *(from phone)* | `John Doe` |
| `customer_email` | Customer's email | *(none)* | `john@example.com` |
| `customer_number` | Member/account number | *(none)* | `ACC12345` |
| `subject` | Ticket subject | `Call from {phone}` | `Payment inquiry` |
| `description` | Ticket description | *(none)* | `Customer called about...` |
| `summary` | AI agent summary | *(none)* | AI conversation summary |
| `sentiment` | Customer sentiment | *(none)* | `positive`, `neutral`, `negative` |
| `customerIntent` | Detected intent | *(none)* | `payment_arrangement` |
| `priority` | Ticket priority | `normal` | `low`, `normal`, `high`, `urgent` |
| `type` | Ticket type | `question` | `question`, `incident`, `problem`, `task` |
| `tags` | Comma-separated tags | `amazon_connect` | `connect,ai_agent,urgent` |
| `custom_fields` | Custom field mappings | *(none)* | `12345=value1,67890=value2` |

## High-Priority Alert Detection

The function automatically detects high-priority intents and applies visual styling:

**Detected Keywords**:
- `fraud`
- `hardship`
- `lost and stolen`
- `lost_stolen`
- `card_lost`
- `card_stolen`

**Result**: 
- 🚨 Red alert banner at top of ticket
- Automatic priority escalation messaging
- Visual styling to draw agent attention

## Ticket Formatting

### Standard Ticket

```
┌─────────────────────────────────────┐
│ 📞 Call Details                     │
├─────────────────────────────────────┤
│ Contact ID: abc-123-def             │
│ Phone Number: +447425162654         │
│ Queue: Support Queue                │
│ Call Type: INBOUND                  │
│ Sentiment: 😊 Positive              │
│ Customer Intent: General Inquiry    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 🤖 AI Agent Summary                 │
├─────────────────────────────────────┤
│ Customer inquired about account     │
│ balance and payment options...      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 👤 Customer Information             │
├─────────────────────────────────────┤
│ Name: Richard Uzzell                │
│ Member Number: MEM12345             │
│ Email: richard.uzzell@example.com   │
└─────────────────────────────────────┘
```

### High-Priority Alert Ticket

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🚨 URGENT: HIGH PRIORITY ALERT    ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ This ticket requires immediate    ┃
┃ attention: FRAUD                  ┃
┃ ⚡ Priority escalation triggered  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┌─────────────────────────────────────┐
│ 📞 Call Details (RED BORDER)        │
│ ...                                 │
└─────────────────────────────────────┘
```

## Examples

See [EXAMPLES.md](EXAMPLES.md) for detailed usage patterns.

**Basic Ticket Creation**:
```python
# Contact flow: Set contact attributes
customer_name = $.External.firstName + " " + $.External.lastName
customer_email = $.External.email
subject = "Inbound call from customer"

# Invoke Lambda
# Returns: ticket_id

# Store for screen pop
zendesk_ticket_id = $.External.ticket_id
```

**With AI Agent Summary**:
```python
# After AI conversation
summary = $.External.aiAgentSummary
sentiment = $.External.aiSentiment
customerIntent = $.External.aiIntent

# Invoke Lambda with all parameters
# High-priority detection automatic
```

## Testing

### Test Event (Lambda Console)

```json
{
  "Details": {
    "ContactData": {
      "ContactId": "test-123",
      "CustomerEndpoint": {"Address": "+447425162654"},
      "Queue": {"Name": "Test Queue"},
      "InitiationMethod": "INBOUND"
    },
    "Parameters": {
      "customer_name": "Test Customer",
      "customer_email": "test@example.com",
      "subject": "Test ticket from Lambda",
      "description": "Testing ticket creation",
      "priority": "normal",
      "tags": "test,lambda"
    }
  }
}
```

**Expected Response**:
```json
{
  "success": "true",
  "ticket_id": "12345",
  "ticket_url": "https://yourcompany.zendesk.com/agent/tickets/12345",
  "contact_id": "test-123"
}
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting.

**Common Issues**:

1. **"Missing Zendesk configuration"** - Set environment variables
2. **"requests module not found"** - Add requests library via Lambda Layer
3. **"401 Unauthorized"** - Check Zendesk API token
4. **Ticket created but no ticket_id** - Check Lambda response in CloudWatch
5. **Screen pop doesn't work** - Verify `zendesk_ticket_id` contact attribute is set

## Screen Pop Integration

### Set Contact Attribute in Contact Flow

After Lambda invocation:
1. Add "Set contact attributes" block
2. **Attribute**: `zendesk_ticket_id`
3. **Value**: `$.External.ticket_id`
4. **Type**: User Defined

### Configure Agent Workspace Screen Pop

**Option A: CTI Adapter**

Use Zendesk Connect CTI adapter with screen pop configuration:
```javascript
{
  "screenPop": {
    "type": "ticket",
    "ticketId": "{{zendesk_ticket_id}}"
  }
}
```

**Option B: Custom CCP**

In your custom Contact Control Panel:
```javascript
contact.onConnected(() => {
  const attributes = contact.getAttributes();
  const ticketId = attributes.zendesk_ticket_id;
  
  if (ticketId) {
    // Open Zendesk ticket in new window or iframe
    window.open(`https://yourcompany.zendesk.com/agent/tickets/${ticketId}`);
  }
});
```

## Related Projects

Other Amazon Connect integrations by Richard Uzzell:

1. **[connect-dynamodb-customer-lookup](https://github.com/RichardUzzellZD/connect-dynamodb-customer-lookup)** - Customer data lookup from DynamoDB
2. **[bankid-connect-integration](https://github.com/RichardUzzellZD/bankid-connect-integration)** - BankID authentication for Connect
3. **[dynamodb-system-status-manager](https://github.com/RichardUzzellZD/dynamodb-system-status-manager)** - System status management via DynamoDB

## License

This is a reference implementation for internal use.

## Author

**Richard Uzzell**  
Email: richard.uzzell@zendesk.com

---

**Quick Start**: Follow [INSTALLATION.md](INSTALLATION.md) to deploy in ~20 minutes.

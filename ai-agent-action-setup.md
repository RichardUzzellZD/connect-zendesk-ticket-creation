# Configure AI Agent Action to Trigger Zendesk Lambda

This setup allows the AI Agent to create a Zendesk ticket during the conversation, ensuring tickets are created even if the customer hangs up before returning to the contact flow.

---

## Step 1: Create Action in Amazon Q

1. Go to **Amazon Connect Console** → **Agent applications** → **Amazon Q**
2. Select your AI Agent (or edit the existing one)
3. Click **Actions** tab
4. Click **Add action**

### Action Configuration:

**Action Name:** `CreateZendeskTicket`

**Description:** `Creates a Zendesk ticket with call details and customer information`

**Lambda function:** Select `CreateZendeskTicketFromConnect`

**Parameters to pass to Lambda:**

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| customer_name | String | No | Customer's full name |
| customer_email | String | No | Customer's email address |
| customer_number | String | No | Medical aid or member number |
| subject | String | Yes | Ticket subject line |
| description | String | Yes | Ticket description with call details |
| priority | String | No | Ticket priority (low, normal, high, urgent) |
| tags | String | No | Comma-separated tags |
| ticket_type | String | No | Ticket type (question, incident, problem, task) |

**Action schema (JSON):**
```json
{
  "actionName": "CreateZendeskTicket",
  "description": "Creates a Zendesk ticket with call details and customer information",
  "parameters": {
    "customer_name": {
      "type": "string",
      "description": "Customer's full name",
      "required": false
    },
    "customer_email": {
      "type": "string",
      "description": "Customer's email address",
      "required": false
    },
    "customer_number": {
      "type": "string",
      "description": "Medical aid or member number",
      "required": false
    },
    "subject": {
      "type": "string",
      "description": "Ticket subject line",
      "required": true
    },
    "description": {
      "type": "string",
      "description": "Detailed description of the call and issue",
      "required": true
    },
    "priority": {
      "type": "string",
      "description": "Ticket priority: low, normal, high, or urgent",
      "required": false
    },
    "tags": {
      "type": "string",
      "description": "Comma-separated tags for the ticket",
      "required": false
    },
    "ticket_type": {
      "type": "string",
      "description": "Type of ticket: question, incident, problem, or task",
      "required": false
    }
  }
}
```

5. Click **Save**

---

## Step 2: Update AI Agent Prompt

Add this section to your AI Agent system prompt:

```yaml
  ### ZENDESK TICKET CREATION
  When you have resolved a customer inquiry and they are satisfied (customer_intent = "claim_resolved"), you MUST create a Zendesk ticket before ending the conversation.
  
  **When to create a ticket:**
    - After successfully explaining claim status
    - After providing benefit information
    - After resolving a general inquiry
    - When customer confirms they are satisfied and ready to end the call
  
  **How to create the ticket:**
  Use the CreateZendeskTicket action with these parameters:
  
    - **customer_name:** Use the verified Full Name (e.g., "Thabo Nkosi")
    - **customer_email:** If available from customer data
    - **customer_number:** Use the Medical Aid Number (e.g., "MEM987654")
    - **subject:** Brief summary (e.g., "Claim inquiry - CLM100293 rejection explained")
    - **description:** Include:
      * Call summary
      * What was discussed
      * What information was provided
      * Claim ID if applicable
      * Any follow-up actions customer needs to take
    - **priority:** "normal" (use "high" for urgent matters)
    - **tags:** "ai_agent,claim_inquiry,claim_resolved" (adjust based on topic)
    - **ticket_type:** "question"
  
  **Workflow:**
    1. Confirm the customer is satisfied
    2. Invoke CreateZendeskTicket action silently (do not announce you are creating a ticket)
    3. Set customer_intent session attribute to "claim_resolved"
    4. Provide closing message (e.g., "Thank you for calling HealthSure Medical Aid. Have a great day.")
    5. Allow customer to hang up or end conversation naturally
  
  **Example ticket description format:**
  ```
  Call handled by AI Agent (Sipho)
  
  Customer: Thabo Nkosi (MEM987654)
  Inquiry: Claim rejection explanation
  Claim ID: CLM100293
  Date of Service: May 10, 2026
  Provider: Dr. Smith
  
  Resolution provided:
  - Explained ERR_01 rejection reason (insufficient MSA funds)
  - Advised customer to settle R650.00 directly with provider
  - Customer confirmed understanding and satisfaction
  
  No further action required.
  ```
```

---

## Step 3: Lambda Modification (Optional)

Your existing `CreateZendeskTicketFromConnect` Lambda already handles parameters from contact flows. It will automatically work with the AI Agent action as well, since the action passes parameters in a compatible format.

**No code changes needed** - the Lambda already extracts parameters from `event.get('Details', {}).get('Parameters', {})` which works for both contact flow invocations and AI Agent actions.

---

## Step 4: Test the Action

### Test in Amazon Q Console:

1. Go to your AI Agent configuration
2. Use the **Test** feature
3. Have a conversation that leads to resolution
4. When you say "Yes, that's all I needed, thank you" (indicating satisfaction)
5. The AI Agent should:
   - Invoke the CreateZendeskTicket action
   - Receive the ticket_id in response
   - Set customer_intent to "claim_resolved"
   - Provide closing message

### Verify:

1. Check **CloudWatch Logs** for the Lambda execution
2. Check **Zendesk** for the created ticket
3. Confirm ticket contains correct customer information and call summary

---

## Benefits of This Approach

✅ **Ticket created even if customer hangs up** - Action is invoked before conversation ends

✅ **No contact flow changes needed** - Ticket creation happens within AI Agent

✅ **Cleaner customer experience** - No delay after AI Agent before disconnect

✅ **Complete call documentation** - Every resolved call creates a ticket automatically

---

## Contact Flow Simplification

With this setup, your contact flow after "Get user input" (AI Agent) becomes simpler:

```
[Get user input - AI Agent]
   ↓
[Check contact attributes]
   - Attribute: $.Session.customer_intent
   
   ↓ claim_resolved
   [Disconnect] (ticket already created by AI Agent)
   
   ↓ payment_arrangement
   [Transfer to Claims Financial Team]
   
   ↓ dispute_claim
   [Invoke Zendesk Lambda] → [Transfer to Claims Resolution]
   
   ↓ transfer_to_agent
   [Transfer to General Queue]
   
   ↓ No match
   [Transfer to General Queue]
```

**Note:** For "claim_resolved", you no longer need to invoke the Lambda in the contact flow since the AI Agent already created the ticket.

---

## Alternative: Create Ticket for ALL Scenarios

If you want to create a ticket for every call regardless of outcome, you can:

1. Have the AI Agent create a ticket at the **start** of the conversation (after verification)
2. Store the ticket_id in a session attribute
3. Update the ticket later if the call gets transferred to an agent (agent can add notes to existing ticket)

This ensures complete call tracking for analytics and compliance.

---

## Troubleshooting

### Action not appearing in AI Agent test

**Problem:** Action not available during conversation

**Solution:** Ensure action is enabled and Lambda has proper permissions for Amazon Connect to invoke it

### Ticket not created

**Problem:** Lambda invoked but ticket not appearing in Zendesk

**Solution:** 
- Check CloudWatch logs for Lambda errors
- Verify ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_API_TOKEN environment variables are set
- Check Lambda response in AI Agent logs

### AI Agent not calling action

**Problem:** AI Agent doesn't invoke CreateZendeskTicket

**Solution:**
- Update prompt to be more explicit about when to call the action
- Test with clear phrases like "I'm satisfied, thank you"
- Check AI Agent configuration that action is associated

---

## Next Steps

1. Configure the action in Amazon Q
2. Update your AI Agent prompt with the ZENDESK TICKET CREATION section
3. Test with a full conversation
4. Monitor CloudWatch logs and Zendesk tickets
5. Adjust prompt instructions based on when tickets should be created

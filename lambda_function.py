"""
Amazon Connect to Zendesk Ticket Creation Lambda

Creates a Zendesk ticket with contact attributes from Amazon Connect.
Returns the ticket ID to be stored in contact attributes for later use.

Environment Variables Required:
- ZENDESK_SUBDOMAIN: Your Zendesk subdomain (e.g., 'mycompany')
- ZENDESK_EMAIL: Zendesk admin email
- ZENDESK_API_TOKEN: Zendesk API token

Example invocation from Connect contact flow:
  Contact Attribute Key -> Lambda Parameter
  CustomerPhone -> customer_phone
  CustomerName -> customer_name
  ContactReason -> contact_reason
"""

import json
import os
import requests
from datetime import datetime


# Zendesk configuration from environment variables
ZENDESK_SUBDOMAIN = os.environ.get('ZENDESK_SUBDOMAIN')
ZENDESK_EMAIL = os.environ.get('ZENDESK_EMAIL')
ZENDESK_API_TOKEN = os.environ.get('ZENDESK_API_TOKEN')

# Zendesk API URL
ZENDESK_URL = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2"


def lambda_handler(event, context):
    """
    Create Zendesk ticket from Amazon Connect contact flow.

    Expected input from Connect:
    {
        "Details": {
            "ContactData": {
                "ContactId": "...",
                "CustomerEndpoint": {"Address": "+447425162654"},
                "Queue": {"Name": "BasicQueue"},
                "InitiationMethod": "INBOUND"
            },
            "Parameters": {
                "customer_phone": "+447425162654",
                "customer_name": "Richard Uzzell",
                "customer_email": "richard.uzzell@example.com",
                "subject": "Inbound call from customer",
                "description": "Customer called regarding...",
                "priority": "normal",
                "tags": "connect,inbound_call"
            }
        }
    }

    Returns (for Connect):
    {
        "ticket_id": "12345",
        "ticket_url": "https://subdomain.zendesk.com/agent/tickets/12345",
        "success": "true"
    }
    """

    print(f"Received event: {json.dumps(event)}")

    try:
        # Validate Zendesk configuration
        if not all([ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_API_TOKEN]):
            return {
                'success': 'false',
                'error': 'Missing Zendesk configuration in Lambda environment variables'
            }

        # Extract contact data from Connect event
        contact_data = event.get('Details', {}).get('ContactData', {})
        parameters = event.get('Details', {}).get('Parameters', {})

        contact_id = contact_data.get('ContactId', 'Unknown')
        customer_phone = contact_data.get('CustomerEndpoint', {}).get('Address', '')
        queue_name = contact_data.get('Queue', {}).get('Name', 'Unknown')
        initiation_method = contact_data.get('InitiationMethod', 'UNKNOWN')

        # Get parameters from contact flow (these are passed from contact attributes)
        customer_name = parameters.get('customer_name', parameters.get('firstName', ''))
        customer_email = parameters.get('customer_email', parameters.get('email', ''))
        customer_number = parameters.get('customer_number', parameters.get('customerNumber', ''))

        # Ticket details
        subject = parameters.get('subject', f'Call from {customer_phone}')
        description = parameters.get('description', '')
        summary = parameters.get('summary', '')
        sentiment = parameters.get('sentiment', '')
        customer_intent = parameters.get('customerIntent', '')
        priority = parameters.get('priority', 'normal')  # low, normal, high, urgent
        ticket_type = parameters.get('type', 'question')  # question, incident, problem, task
        tags_str = parameters.get('tags', 'amazon_connect')

        # Parse tags (comma-separated string to list)
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

        # Build HTML-formatted ticket description

        # Check if this is a high-priority alert intent
        high_priority_intents = ['fraud', 'hardship', 'lost and stolen', 'lost_stolen', 'card_lost', 'card_stolen']
        is_high_priority = any(keyword in customer_intent.lower() for keyword in high_priority_intents)

        # Sentiment styling
        sentiment_colors = {
            'positive': {'bg': '#d4edda', 'text': '#155724', 'emoji': '😊'},
            'neutral': {'bg': '#fff3cd', 'text': '#856404', 'emoji': '😐'},
            'negative': {'bg': '#f8d7da', 'text': '#721c24', 'emoji': '😟'}
        }
        sentiment_style = sentiment_colors.get(sentiment.lower(), {'bg': '#e2e3e5', 'text': '#383d41', 'emoji': '❓'})

        # Customer intent styling
        intent_colors = {
            'transfer to agent': {'bg': '#ff6b6b', 'text': '#ffffff'},
            'claim_resolved': {'bg': '#51cf66', 'text': '#ffffff'},
            'payment_arrangement': {'bg': '#ffa94d', 'text': '#ffffff'},
            'urgent_emergency': {'bg': '#ff0000', 'text': '#ffffff'}
        }
        intent_style = intent_colors.get(customer_intent.lower(), {'bg': '#868e96', 'text': '#ffffff'})

        # Build HTML content
        html_parts = [
            '<div style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Arial, sans-serif; max-width: 800px; color: #333;">'
        ]

        # Add high-priority alert banner if applicable
        if is_high_priority:
            html_parts.extend([
                '<div style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); border: 3px solid #7f1d1d; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4);">',
                '<div style="display: flex; align-items: center; margin-bottom: 12px;">',
                '<span style="font-size: 32px; margin-right: 12px;">🚨</span>',
                '<h2 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">URGENT: HIGH PRIORITY ALERT</h2>',
                '</div>',
                f'<p style="margin: 0; color: #fecaca; font-size: 15px; font-weight: 600; line-height: 1.5;">This ticket requires immediate attention: <span style="color: #ffffff; background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px;">{customer_intent.upper()}</span></p>',
                '<p style="margin: 10px 0 0 0; color: #fef2f2; font-size: 13px; font-style: italic;">⚡ Priority escalation triggered by AI Agent detection</p>',
                '</div>'
            ])

        # Call Details Section with conditional styling
        call_details_border_color = '#dc2626' if is_high_priority else '#2c5282'
        call_details_bg = '#fff5f5' if is_high_priority else '#f8f9fa'
        call_details_title_color = '#dc2626' if is_high_priority else '#2c5282'

        html_parts.extend([
            f'<div style="background: {call_details_bg}; border-left: 4px solid {call_details_border_color}; padding: 20px; margin-bottom: 20px; border-radius: 4px;">',
            f'<h3 style="margin: 0 0 15px 0; color: {call_details_title_color}; font-size: 16px;">📞 Call Details</h3>',
            '<table style="width: 100%; border-collapse: collapse; font-size: 14px;">',
            f'<tr><td style="padding: 8px 12px; font-weight: 600; width: 40%; background: #ffffff;">Contact ID</td><td style="padding: 8px 12px; background: #ffffff;">{contact_id}</td></tr>',
            f'<tr><td style="padding: 8px 12px; font-weight: 600; background: #f8f9fa;">Phone Number</td><td style="padding: 8px 12px; background: #f8f9fa;">{customer_phone}</td></tr>',
            f'<tr><td style="padding: 8px 12px; font-weight: 600; background: #ffffff;">Queue</td><td style="padding: 8px 12px; background: #ffffff;">{queue_name}</td></tr>',
            f'<tr><td style="padding: 8px 12px; font-weight: 600; background: #f8f9fa;">Call Type</td><td style="padding: 8px 12px; background: #f8f9fa;">{initiation_method}</td></tr>',
            f'<tr><td style="padding: 8px 12px; font-weight: 600; background: #ffffff;">Timestamp</td><td style="padding: 8px 12px; background: #ffffff;">{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</td></tr>'
        ])

        # Add sentiment row if provided
        if sentiment:
            html_parts.append(
                f'<tr><td style="padding: 8px 12px; font-weight: 600; background: #f8f9fa;">Sentiment</td>'
                f'<td style="padding: 8px 12px; background: #f8f9fa;">'
                f'<span style="background: {sentiment_style["bg"]}; color: {sentiment_style["text"]}; padding: 4px 12px; border-radius: 12px; font-weight: 600; display: inline-block;">'
                f'{sentiment_style["emoji"]} {sentiment.title()}</span></td></tr>'
            )

        # Add customer intent row if provided
        if customer_intent:
            # Override intent styling for high-priority cases
            if is_high_priority:
                intent_badge_style = 'background: #dc2626; color: #ffffff; padding: 6px 14px; border-radius: 12px; font-weight: 700; display: inline-block; border: 2px solid #991b1b; box-shadow: 0 2px 4px rgba(220, 38, 38, 0.3);'
                intent_prefix = '🚨 '
            else:
                intent_badge_style = f'background: {intent_style["bg"]}; color: {intent_style["text"]}; padding: 4px 12px; border-radius: 12px; font-weight: 600; display: inline-block;'
                intent_prefix = ''

            html_parts.append(
                f'<tr><td style="padding: 8px 12px; font-weight: 600; background: #ffffff;">Customer Intent</td>'
                f'<td style="padding: 8px 12px; background: #ffffff;">'
                f'<span style="{intent_badge_style}">'
                f'{intent_prefix}{customer_intent.title()}</span></td></tr>'
            )

        html_parts.extend([
            '</table>',
            '</div>'
        ])

        # AI Agent Summary or Description Section
        if summary:
            html_parts.extend([
                '<div style="background: #e7f5ff; border-left: 4px solid #1c7ed6; padding: 20px; margin-bottom: 20px; border-radius: 4px;">',
                '<h3 style="margin: 0 0 12px 0; color: #1c7ed6; font-size: 16px;">🤖 AI Agent Summary</h3>',
                f'<p style="margin: 0; line-height: 1.6; font-size: 14px; white-space: pre-wrap;">{summary}</p>',
                '</div>'
            ])
        elif description:
            html_parts.extend([
                '<div style="background: #f1f3f5; border-left: 4px solid #495057; padding: 20px; margin-bottom: 20px; border-radius: 4px;">',
                '<h3 style="margin: 0 0 12px 0; color: #495057; font-size: 16px;">📝 Notes</h3>',
                f'<p style="margin: 0; line-height: 1.6; font-size: 14px; white-space: pre-wrap;">{description}</p>',
                '</div>'
            ])

        # Customer Information Section (if available)
        if customer_name or customer_number:
            html_parts.extend([
                '<div style="background: #fff4e6; border-left: 4px solid #fd7e14; padding: 20px; border-radius: 4px;">',
                '<h3 style="margin: 0 0 12px 0; color: #fd7e14; font-size: 16px;">👤 Customer Information</h3>',
                '<table style="width: 100%; border-collapse: collapse; font-size: 14px;">'
            ])

            if customer_name:
                html_parts.append(f'<tr><td style="padding: 8px 12px; font-weight: 600; width: 40%;">Name</td><td style="padding: 8px 12px;">{customer_name}</td></tr>')
            if customer_number:
                html_parts.append(f'<tr><td style="padding: 8px 12px; font-weight: 600; background: #fff9db;">Member Number</td><td style="padding: 8px 12px; background: #fff9db;">{customer_number}</td></tr>')
            if customer_email:
                html_parts.append(f'<tr><td style="padding: 8px 12px; font-weight: 600;">Email</td><td style="padding: 8px 12px;">{customer_email}</td></tr>')

            html_parts.extend([
                '</table>',
                '</div>'
            ])

        html_parts.append('</div>')

        call_details_html = ''.join(html_parts)

        # Prepare Zendesk ticket payload
        ticket_payload = {
            "ticket": {
                "subject": subject,
                "comment": {
                    "html_body": call_details_html
                },
                "priority": priority,
                "type": ticket_type,
                "tags": tags,
                "custom_fields": []
            }
        }

        # Add requester info if available
        if customer_email:
            ticket_payload["ticket"]["requester"] = {
                "name": customer_name if customer_name else customer_phone,
                "email": customer_email
            }
        elif customer_name or customer_phone:
            # Use name field for phone if no email
            ticket_payload["ticket"]["requester"] = {
                "name": customer_name if customer_name else f"Customer {customer_phone}"
            }

        # Add custom fields if provided (format: field_id=value)
        custom_fields_param = parameters.get('custom_fields', '')
        if custom_fields_param:
            for field_def in custom_fields_param.split(','):
                if '=' in field_def:
                    field_id, field_value = field_def.split('=', 1)
                    ticket_payload["ticket"]["custom_fields"].append({
                        "id": int(field_id.strip()),
                        "value": field_value.strip()
                    })

        # Add Amazon Connect contact ID as custom field if specified
        contact_id_field = parameters.get('contact_id_field')
        if contact_id_field:
            ticket_payload["ticket"]["custom_fields"].append({
                "id": int(contact_id_field),
                "value": contact_id
            })

        print(f"Creating Zendesk ticket with payload: {json.dumps(ticket_payload)}")

        # Create Zendesk ticket
        response = requests.post(
            f"{ZENDESK_URL}/tickets.json",
            json=ticket_payload,
            auth=(f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        response.raise_for_status()

        # Parse response
        ticket_data = response.json().get('ticket', {})
        ticket_id = str(ticket_data.get('id', ''))
        ticket_url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/agent/tickets/{ticket_id}"

        print(f"Successfully created Zendesk ticket {ticket_id}")

        # Return ticket info to Amazon Connect
        return {
            'success': 'true',
            'ticket_id': ticket_id,
            'ticket_url': ticket_url,
            'contact_id': contact_id
        }

    except requests.exceptions.RequestException as e:
        error_msg = f"Zendesk API error: {str(e)}"
        print(error_msg)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response body: {e.response.text}")
        return {
            'success': 'false',
            'error': error_msg
        }

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return {
            'success': 'false',
            'error': error_msg
        }

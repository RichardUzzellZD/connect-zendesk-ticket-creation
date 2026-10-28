#!/bin/bash

# Deployment script for Amazon Connect to Zendesk Lambda
# Region: eu-west-2
# Account: 989571800624

set -e

FUNCTION_NAME="CreateZendeskTicketFromConnect"
REGION="eu-west-2"
ROLE_NAME="LambdaZendeskConnectRole"
ACCOUNT_ID="989571800624"

echo "🚀 Deploying Zendesk Ticket Creation Lambda"
echo "============================================"

# Step 1: Create deployment package
echo "📦 Creating deployment package..."
cd "$(dirname "$0")"
pip install -r requirements.txt -t package/
cp create_zendesk_ticket_lambda.py package/lambda_function.py
cd package
zip -r ../lambda_deployment.zip .
cd ..
echo "✅ Package created"

# Step 2: Check if IAM role exists, create if not
echo "🔐 Checking IAM role..."
if aws iam get-role --role-name $ROLE_NAME --region $REGION 2>/dev/null; then
    echo "✅ Role exists"
else
    echo "Creating IAM role..."

    # Create trust policy
    cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    aws iam create-role \
      --role-name $ROLE_NAME \
      --assume-role-policy-document file://trust-policy.json \
      --region $REGION

    # Attach CloudWatch Logs policy
    aws iam attach-role-policy \
      --role-name $ROLE_NAME \
      --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
      --region $REGION

    echo "✅ Role created, waiting 10 seconds for propagation..."
    sleep 10
fi

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

# Step 3: Create or update Lambda function
echo "⚡ Deploying Lambda function..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing function..."
    aws lambda update-function-code \
      --function-name $FUNCTION_NAME \
      --zip-file fileb://lambda_deployment.zip \
      --region $REGION

    echo "Waiting for update to complete..."
    aws lambda wait function-updated \
      --function-name $FUNCTION_NAME \
      --region $REGION

    echo "✅ Function updated"
else
    echo "Creating new function..."
    aws lambda create-function \
      --function-name $FUNCTION_NAME \
      --runtime python3.11 \
      --role $ROLE_ARN \
      --handler lambda_function.lambda_handler \
      --zip-file fileb://lambda_deployment.zip \
      --timeout 30 \
      --memory-size 256 \
      --environment Variables={ZENDESK_SUBDOMAIN=YOUR_SUBDOMAIN,ZENDESK_EMAIL=YOUR_EMAIL,ZENDESK_API_TOKEN=YOUR_TOKEN} \
      --region $REGION

    echo "⚠️  Remember to update environment variables with your Zendesk credentials!"
    echo "✅ Function created"
fi

# Step 4: Add Amazon Connect permission
echo "📞 Adding Amazon Connect permission..."
aws lambda add-permission \
  --function-name $FUNCTION_NAME \
  --statement-id AllowConnectInvoke \
  --action lambda:InvokeFunction \
  --principal connect.amazonaws.com \
  --source-arn arn:aws:connect:${REGION}:${ACCOUNT_ID}:instance/b286a3d1-0bde-477d-878d-67c3c8819aff \
  --region $REGION 2>/dev/null || echo "⚠️  Permission already exists (this is OK)"

# Step 5: Associate with Connect instance
echo "🔗 Associating with Amazon Connect..."
aws connect associate-lambda-function \
  --instance-id b286a3d1-0bde-477d-878d-67c3c8819aff \
  --function-arn arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME} \
  --region $REGION 2>/dev/null || echo "⚠️  Already associated (this is OK)"

# Cleanup
rm -rf package/
rm lambda_deployment.zip
rm -f trust-policy.json

echo ""
echo "✅ Deployment complete!"
echo "============================================"
echo "Lambda ARN: arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"
echo ""
echo "⚠️  IMPORTANT: Update Lambda environment variables with your Zendesk credentials:"
echo "   ZENDESK_SUBDOMAIN=your-subdomain"
echo "   ZENDESK_EMAIL=your-email@company.com"
echo "   ZENDESK_API_TOKEN=your-api-token"
echo ""
echo "Next steps:"
echo "1. Update environment variables in Lambda console or via CLI"
echo "2. Add Lambda to your Amazon Connect contact flow"
echo "3. Test by making a call"

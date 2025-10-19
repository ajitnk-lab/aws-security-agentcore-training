# Layer 1: React UI on S3 - Complete Guide

## Overview

Deploy React application to S3 for static website hosting with two phases:
- **Phase 1 (Dev)**: Public S3 website - fast iteration
- **Phase 2 (Prod)**: Private S3 + CloudFront OAC - secure production

---

## Prerequisites

### Required Tools
```bash
# Node.js and npm
node --version  # v16+ recommended
npm --version   # v8+ recommended

# AWS CLI
aws --version   # v2.x recommended
aws configure   # Must be configured
```

### AWS Permissions Required
- `s3:CreateBucket`, `s3:PutObject`, `s3:PutBucketPolicy`, `s3:PutBucketWebsite`
- `s3:PutPublicAccessBlock` (for Phase 1)
- `cloudfront:*` (for Phase 2)

---

## Phase 1: Public S3 Website (Development)

### Step 1: React Project Setup

**package.json** (minimal example):
```json
{
  "name": "security-chatbot-ui",
  "version": "1.0.0",
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "deploy": "./deploy-ui.sh"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0"
  }
}
```

**Environment Variables** (.env):
```bash
REACT_APP_API_URL=https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod
```

### Step 2: Deployment Script

Create `deploy-ui.sh` in project root:

```bash
#!/bin/bash
set -e

echo "🚀 React UI Deployment Script - Phase 1 (Public S3)"
echo "=================================================="

# Prompt for bucket name
read -p "Enter S3 bucket name (e.g., my-app-ui-dev): " BUCKET_NAME

# Prompt for AWS region
read -p "Enter AWS region [us-east-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

# Prompt for API Gateway URL
read -p "Enter API Gateway URL (optional): " API_URL

echo ""
echo "Configuration:"
echo "  Bucket: $BUCKET_NAME"
echo "  Region: $AWS_REGION"
echo "  API URL: ${API_URL:-Not set}"
echo ""
read -p "Continue? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Set API URL if provided
if [ ! -z "$API_URL" ]; then
    export REACT_APP_API_URL=$API_URL
fi

# Step 1: Build React app
echo ""
echo "📦 Step 1: Building React app..."
npm run build

if [ ! -d "build" ]; then
    echo "❌ Error: build/ directory not found"
    exit 1
fi

echo "✅ Build complete"

# Step 2: Create S3 bucket if it doesn't exist
echo ""
echo "🪣 Step 2: Checking S3 bucket..."

if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating bucket $BUCKET_NAME..."
    aws s3 mb "s3://$BUCKET_NAME" --region "$AWS_REGION"
    echo "✅ Bucket created"
else
    echo "✅ Bucket exists"
fi

# Step 3: Disable Block Public Access
echo ""
echo "🔓 Step 3: Configuring public access..."
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

echo "✅ Public access enabled"

# Step 4: Enable static website hosting
echo ""
echo "🌐 Step 4: Enabling static website hosting..."
aws s3 website "s3://$BUCKET_NAME" \
    --index-document index.html \
    --error-document index.html

echo "✅ Website hosting enabled"

# Step 5: Set bucket policy for public read
echo ""
echo "📜 Step 5: Setting bucket policy..."
cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
    --bucket "$BUCKET_NAME" \
    --policy file:///tmp/bucket-policy.json

rm /tmp/bucket-policy.json
echo "✅ Bucket policy set"

# Step 6: Sync build files to S3
echo ""
echo "📤 Step 6: Uploading files to S3..."
aws s3 sync build/ "s3://$BUCKET_NAME" \
    --delete \
    --cache-control "max-age=31536000" \
    --exclude "index.html" \
    --exclude "*.map"

# Upload index.html with no cache
aws s3 cp build/index.html "s3://$BUCKET_NAME/index.html" \
    --cache-control "no-cache, no-store, must-revalidate"

echo "✅ Files uploaded"

# Step 7: Get website URL
WEBSITE_URL="http://$BUCKET_NAME.s3-website-$AWS_REGION.amazonaws.com"

echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "Website URL: $WEBSITE_URL"
echo ""
echo "Test your deployment:"
echo "  curl $WEBSITE_URL"
echo ""
echo "⚠️  Note: This is HTTP only (not HTTPS)"
echo "⚠️  For HTTPS, use Phase 2 (CloudFront + OAC)"
echo ""
```

Make it executable:
```bash
chmod +x deploy-ui.sh
```

### Step 3: Deploy

```bash
./deploy-ui.sh
```

---

## Common Issues & Solutions

### Issue 1: "Build directory not found"
**Cause**: `npm run build` failed or wrong directory
**Solution**:
```bash
# Check if build succeeded
npm run build
ls -la build/

# Verify package.json has build script
cat package.json | grep "build"
```

### Issue 2: "Access Denied" when syncing
**Cause**: AWS CLI not configured or wrong permissions
**Solution**:
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify S3 permissions
aws iam get-user-policy --user-name YOUR_USER --policy-name YOUR_POLICY
```

### Issue 3: "403 Forbidden" when accessing website
**Cause**: Block Public Access still enabled or bucket policy missing
**Solution**:
```bash
# Check Block Public Access
aws s3api get-public-access-block --bucket YOUR_BUCKET

# Check bucket policy
aws s3api get-bucket-policy --bucket YOUR_BUCKET

# Re-run steps 3-5 from deploy script
```

### Issue 4: "404 on page refresh" (SPA routing)
**Cause**: S3 returns 404 for routes like `/dashboard`
**Solution**: Error document set to `index.html` (already in script)
```bash
aws s3 website s3://YOUR_BUCKET \
    --index-document index.html \
    --error-document index.html
```

### Issue 5: "Old version still showing"
**Cause**: Browser cache or CDN cache
**Solution**:
```bash
# Clear browser cache (Ctrl+Shift+R)
# Or use incognito mode

# Check what's actually in S3
aws s3 ls s3://YOUR_BUCKET/ --recursive
```

### Issue 6: "Wrong bucket deployed to"
**Cause**: Deployed to wrong environment bucket
**Solution**: Script now prompts for bucket name - double check before confirming

---

## Phase 2: Private S3 + CloudFront OAC (Production)

### When to Use Phase 2
- ✅ Development complete
- ✅ Ready for production
- ✅ Need HTTPS
- ✅ Need better security
- ✅ Need CDN performance

### Migration Script

Create `deploy-ui-prod.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 React UI Deployment Script - Phase 2 (CloudFront + OAC)"
echo "=========================================================="

# [Script continues with CloudFront setup...]
# Full script available in examples/deploy-ui-prod.sh
```

---

## Best Practices

### 1. **Environment Variables**
```bash
# .env.development
REACT_APP_API_URL=http://localhost:3000

# .env.production
REACT_APP_API_URL=https://api.example.com/prod
```

### 2. **Cache Control**
- **index.html**: No cache (always fresh)
- **JS/CSS/Images**: Long cache (1 year) with hashed filenames

### 3. **Build Optimization**
```json
{
  "scripts": {
    "build": "GENERATE_SOURCEMAP=false react-scripts build"
  }
}
```

### 4. **Security Headers** (Phase 2 with CloudFront)
- Add security headers via CloudFront Functions
- HSTS, CSP, X-Frame-Options

---

## Troubleshooting Checklist

Before deploying:
- [ ] `npm run build` succeeds
- [ ] `build/` directory exists
- [ ] AWS CLI configured (`aws sts get-caller-identity`)
- [ ] Correct bucket name
- [ ] Correct region

After deploying:
- [ ] Website URL accessible
- [ ] No 403/404 errors
- [ ] API calls work (check browser console)
- [ ] SPA routing works (refresh on sub-routes)

---

## Cost Considerations

### Phase 1 (Public S3)
- **S3 Storage**: ~$0.023/GB/month
- **S3 Requests**: $0.0004 per 1K GET requests
- **Data Transfer**: $0.09/GB (first 10TB)

**Example**: 100MB app, 1K users/day
- Storage: $0.002/month
- Requests: ~$0.12/month
- Transfer: ~$2.70/month
- **Total**: ~$3/month

### Phase 2 (CloudFront + S3)
- **CloudFront**: $0.085/GB (first 10TB)
- **S3**: Same as above
- **CloudFront Requests**: $0.0075 per 10K HTTPS requests

**Example**: Same usage
- **Total**: ~$2.50/month (cheaper + faster!)

---

## Next Layer

Once UI is deployed, proceed to:
- **[Layer 2: API Gateway](./02-API-GATEWAY.md)** - Connect UI to backend

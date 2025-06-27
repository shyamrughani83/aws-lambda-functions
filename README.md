# 💰 AWS Cost Optimization Lambda Function

This AWS Lambda function automatically detects AWS services incurring charges and attempts to **stop**, **pause**, or **disable** resources where applicable — helping you reduce costs in real time.

## 📌 Features

- ✅ Dynamically fetches cost data from AWS Cost Explorer
- ✅ Automatically detects which AWS services are charging
- ✅ Attempts to stop/pause/disable resources for those services (if supported)
- ✅ No hardcoded service list — fully extensible and dynamic
- ✅ Safe: **Does not delete** any resources
- 🛠 Easily extensible: Add handlers for more services

---

## 🧠 How It Works

1. Uses `boto3` to query AWS **Cost Explorer** for all services incurring charges this month.
2. Normalizes the service names to Python-safe handler function names.
3. Calls handler functions like `handle_amazon_ec2`, `handle_amazon_rds`, etc., if defined.
4. Skips services where no handler is implemented.
5. Returns a report of actions taken and cost breakdown.

---

## 📦 Supported Services

The function currently handles:

- EC2 Instances
- RDS Instances
- ELBv2 (reports only)
- SageMaker Notebooks
- AWS Batch
- WorkSpaces
- Neptune Clusters
- DocumentDB Clusters
- Amazon MQ
- AppStream Fleets
- Redshift Clusters
- AWS Transfer Family
- AWS DataSync
- Lightsail Instances

> Add more service handlers as needed using the naming format: `handle_<normalized_service_name>`.

---

## 🚀 Deployment

### Prerequisites

- Python 3.8+ runtime
- IAM role with permissions to:
  - `ce:GetCostAndUsage`
  - `ec2:DescribeInstances`, `ec2:StopInstances`, etc.
  - Service-specific actions like `rds:StopDBInstance`, `sagemaker:StopNotebookInstance`, etc.

### Steps

1. Zip the Lambda code:
   ```bash
   zip -r cost-optimizer.zip .
Create the Lambda function:

bash
Copy
Edit
aws lambda create-function \
  --function-name CostOptimizerLambda \
  --runtime python3.8 \
  --role arn:aws:iam::<account-id>:role/<lambda-execution-role> \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://cost-optimizer.zip
(Optional) Add a CloudWatch or EventBridge trigger to run daily or connect to an AWS Budget alarm.

🧪 Testing
To test manually in the Lambda console:

json
Copy
Edit
{
  "trigger": "manual"
}

### Shyam Rughani (Cloud Man)

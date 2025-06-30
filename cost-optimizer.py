AWSTemplateFormatVersion: '2010-09-09'
Description: Lambda that stops AWS resources based on cost (with required IAM role)

Resources:

  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: LambdaCostOptimizerRole
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: LambdaCostOptimizerPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - ec2:DescribeInstances
                  - ec2:StopInstances
                  - rds:DescribeDBInstances
                  - rds:StopDBInstance
                  - ce:GetCostAndUsage
                  - elasticloadbalancing:DescribeLoadBalancers
                  - batch:DescribeJobQueues
                  - batch:UpdateJobQueue
                  - sagemaker:ListNotebookInstances
                  - sagemaker:StopNotebookInstance
                  - workspaces:DescribeWorkspaces
                  - workspaces:StopWorkspaces
                  - neptune:DescribeDBClusters
                  - neptune:StopDBCluster
                  - docdb:DescribeDBClusters
                  - docdb:StopDBCluster
                  - mq:ListBrokers
                  - mq:RebootBroker
                  - appstream:DescribeFleets
                  - appstream:StopFleet
                  - redshift:DescribeClusters
                  - redshift:PauseCluster
                  - transfer:ListServers
                  - transfer:StopServer
                  - datasync:ListTasks
                  - datasync:UpdateTask
                  - lightsail:GetInstances
                  - lightsail:StopInstance
                Resource: "*"

  CostOptimizerLambda:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: CostOptimizerLambda
      Handler: index.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Runtime: python3.12
      Timeout: 300
      Code:
        ZipFile: |
          import boto3
          import datetime
          import re

          session = boto3.session.Session()
          region = session.region_name
          ce = session.client('ce')
          ec2 = session.client('ec2')
          rds = session.client('rds')
          elbv2 = session.client('elbv2')

          def get_today_date_range():
              today = datetime.date.today()
              start = today.replace(day=1).isoformat()
              end = today.isoformat()
              return start, end

          def normalize_service_name(service_name):
              return re.sub(r'[^a-z0-9_]', '_', service_name.lower())

          def get_cost_breakdown_with_charges_only():
              start, end = get_today_date_range()
              results = []
              next_token = None

              while True:
                  params = {
                      'TimePeriod': {'Start': start, 'End': end},
                      'Granularity': 'MONTHLY',
                      'Metrics': ['UnblendedCost'],
                      'GroupBy': [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
                  }
                  if next_token:
                      params['NextPageToken'] = next_token

                  response = ce.get_cost_and_usage(**params)
                  results.extend(response['ResultsByTime'][0]['Groups'])
                  next_token = response.get('NextPageToken')
                  if not next_token:
                      break

              service_costs = {}
              print(f"📊 === Services with Charges (From {start} to {end}) === 📊")
              print(f"{'Service':<45} {'Cost ($)':>10}")
              print("-" * 60)
              for group in results:
                  service = group['Keys'][0]
                  amount = float(group['Metrics']['UnblendedCost']['Amount'])
                  if amount > 0.0:
                      service_costs[service] = amount
                      print(f"{service:<45} {amount:>10.2f}")
              print("-" * 60)
              return service_costs, start, end

          def handle_amazon_elastic_compute_cloud___compute():
              instances = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
              ids = []
              names = []
              for reservation in instances['Reservations']:
                  for instance in reservation['Instances']:
                      ids.append(instance['InstanceId'])
                      name = None
                      for tag in instance.get('Tags', []):
                          if tag['Key'] == 'Name':
                              name = tag['Value']
                              break
                      names.append(name if name else "(No Name)")
              if ids:
                  ec2.stop_instances(InstanceIds=ids)
                  for i, n in zip(ids, names):
                      print(f"🛑 Stopped EC2 instance: ID={i}, Name={n}")
              else:
                  print("✅ No running EC2 instances.")

          def handle_ec2___other():
              return handle_amazon_elastic_compute_cloud___compute()

          def lambda_handler(event, context):
              print(f"🌍 Running in region: {region}")
              service_costs, start_date, end_date = get_cost_breakdown_with_charges_only()
              actions_taken = []

              for service, cost in service_costs.items():
                  print(f"⚙️ Handling: {service} (${cost:.2f})")
                  try:
                      handler_name = f"handle_{normalize_service_name(service)}"
                      handler = globals().get(handler_name)
                      if callable(handler):
                          handler()
                          actions_taken.append(service)
                      else:
                          print(f"⚠️ No handler defined for: {service}")
                  except Exception as e:
                      print(f"❌ Error handling {service}: {e}")

              return {
                  "status": "done",
                  "region": region,
                  "billing_period_start": start_date,
                  "billing_period_end": end_date,
                  "services_with_cost": list(service_costs.keys()),
                  "actions_taken": actions_taken
              }

Outputs:
  LambdaFunctionName:
    Description: Lambda function name
    Value: !Ref CostOptimizerLambda

  LambdaRoleArn:
    Description: Lambda IAM Role ARN
    Value: !GetAtt LambdaExecutionRole.Arn

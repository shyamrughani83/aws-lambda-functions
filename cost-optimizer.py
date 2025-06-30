
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

def handle_amazon_relational_database_service():
    instances = rds.describe_db_instances()
    ids = [db['DBInstanceIdentifier'] for db in instances['DBInstances'] if db['DBInstanceStatus'] == 'available']
    for db_id in ids:
        rds.stop_db_instance(DBInstanceIdentifier=db_id)
        print(f"🛑 Stopped RDS instance: {db_id}")
    if not ids:
        print("✅ No available RDS instances.")

def handle_amazon_elastic_load_balancing():
    lbs = elbv2.describe_load_balancers()
    names = [lb['LoadBalancerArn'] for lb in lbs['LoadBalancers']]
    if names:
        print(f"⚠️ ELBs exist: {names} — not deleting for safety.")
    else:
        print("✅ No ELBs found.")

def call_handler_for_service(service_name):
    handler_name = f"handle_{normalize_service_name(service_name)}"
    handler = globals().get(handler_name)
    if callable(handler):
        handler()
        return True
    return False

def lambda_handler(event, context):
    print(f"🌍 Running in region: {region}")
    service_costs, start_date, end_date = get_cost_breakdown_with_charges_only()
    actions_taken = []

    for service, cost in service_costs.items():
        if cost == 0.0:
            continue
        print(f"⚙️ Handling: {service} (${cost:.2f})")
        try:
            if call_handler_for_service(service):
                actions_taken.append(service)
            else:
                print(f"✅ No resources to stop for: {service}")
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

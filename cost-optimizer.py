import boto3
import datetime
import re

# === AWS Clients ===
session = boto3.session.Session()
region = session.region_name
ce = session.client('ce')
ec2 = session.client('ec2')
rds = session.client('rds')
elbv2 = session.client('elbv2')

# === Utility Functions ===
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

# === Handlers ===

def handle_amazon_elastic_compute_cloud___compute():
    instances = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    ids = [i['InstanceId'] for r in instances['Reservations'] for i in r['Instances']]
    if ids:
        ec2.stop_instances(InstanceIds=ids)
        print(f"🛑 Stopped EC2 instances: {ids}")
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
    try:
        lbs = elbv2.describe_load_balancers()
        names = [lb['LoadBalancerArn'] for lb in lbs['LoadBalancers']]
        if names:
            print(f"⚠️ ELBs exist: {names} — not deleting for safety.")
        else:
            print("✅ No ELBs found.")
    except Exception as e:
        print(f"❌ Error checking ELBs: {e}")

def handle_aws_batch():
    batch = session.client('batch')
    queues = batch.describe_job_queues()['jobQueues']
    for q in queues:
        if q['state'] == 'ENABLED':
            batch.update_job_queue(jobQueue=q['jobQueueName'], state='DISABLED')
            print(f"🛑 Disabled Batch Job Queue: {q['jobQueueName']}")
    if not queues:
        print("✅ No Batch Job Queues found.")

def handle_amazon_sagemaker():
    sagemaker = session.client('sagemaker')
    notebooks = sagemaker.list_notebook_instances()['NotebookInstances']
    for nb in notebooks:
        if nb['NotebookInstanceStatus'] == 'InService':
            sagemaker.stop_notebook_instance(NotebookInstanceName=nb['NotebookInstanceName'])
            print(f"🛑 Stopped SageMaker notebook: {nb['NotebookInstanceName']}")

def handle_amazon_workspaces():
    workspaces = session.client('workspaces')
    ws_list = workspaces.describe_workspaces()['Workspaces']
    ids = [ws['WorkspaceId'] for ws in ws_list if ws['State'] == 'AVAILABLE']
    if ids:
        workspaces.stop_workspaces(StopWorkspaceRequests=[{'WorkspaceId': wid} for wid in ids])
        print(f"🛑 Stopped WorkSpaces: {ids}")
    else:
        print("✅ No WorkSpaces to stop.")

def handle_amazon_neptune():
    neptune = session.client('neptune')
    clusters = neptune.describe_db_clusters()['DBClusters']
    for cluster in clusters:
        if cluster['Status'] == 'available':
            neptune.stop_db_cluster(DBClusterIdentifier=cluster['DBClusterIdentifier'])
            print(f"🛑 Stopped Neptune cluster: {cluster['DBClusterIdentifier']}")

def handle_amazon_documentdb():
    docdb = session.client('docdb')
    clusters = docdb.describe_db_clusters()['DBClusters']
    for cluster in clusters:
        if cluster['Status'] == 'available':
            docdb.stop_db_cluster(DBClusterIdentifier=cluster['DBClusterIdentifier'])
            print(f"🛑 Stopped DocumentDB cluster: {cluster['DBClusterIdentifier']}")

def handle_amazon_mq():
    mq = session.client('mq')
    brokers = mq.list_brokers()['BrokerSummaries']
    for broker in brokers:
        if broker['BrokerState'] == 'RUNNING':
            mq.reboot_broker(BrokerId=broker['BrokerId'])
            print(f"⚠️ Rebooted Amazon MQ broker (no stop API): {broker['BrokerId']}")

def handle_amazon_appstream():
    appstream = session.client('appstream')
    fleets = appstream.describe_fleets()['Fleets']
    for fleet in fleets:
        if fleet['State'] == 'RUNNING':
            appstream.stop_fleet(Name=fleet['Name'])
            print(f"🛑 Stopped AppStream fleet: {fleet['Name']}")

def handle_amazon_redshift():
    redshift = session.client('redshift')
    clusters = redshift.describe_clusters()['Clusters']
    for cluster in clusters:
        if cluster['ClusterAvailabilityStatus'] == 'Available':
            redshift.pause_cluster(ClusterIdentifier=cluster['ClusterIdentifier'])
            print(f"⏸️ Paused Redshift cluster: {cluster['ClusterIdentifier']}")

def handle_aws_transfer_for_sftp():
    transfer = session.client('transfer')
    servers = transfer.list_servers()['Servers']
    for server in servers:
        if server['State'] == 'ONLINE':
            transfer.stop_server(ServerId=server['ServerId'])
            print(f"🛑 Stopped Transfer Family server: {server['ServerId']}")

def handle_aws_datasync():
    datasync = session.client('datasync')
    tasks = datasync.list_tasks()['Tasks']
    for task in tasks:
        datasync.update_task(TaskArn=task['TaskArn'], Options={"VerifyMode": "NONE"})
        print(f"⚠️ Updated DataSync task to reduce cost: {task['TaskArn']}")

def handle_amazon_lightsail():
    lightsail = session.client('lightsail')
    instances = lightsail.get_instances()['instances']
    names = [ins['name'] for ins in instances if ins['state']['name'] == 'running']
    if names:
        for name in names:
            lightsail.stop_instance(instanceName=name)
        print(f"🛑 Stopped Lightsail instances: {names}")
    else:
        print("✅ No running Lightsail instances.")

# === Dispatcher ===
def call_handler_for_service(service_name):
    handler_name = f"handle_{normalize_service_name(service_name)}"
    handler = globals().get(handler_name)
    if callable(handler):
        handler()
        return True
    return False

# === Lambda Entry Point ===
def lambda_handler(event, context):
    print(f"�� Running in region: {region}")
    service_costs, start_date, end_date = get_cost_breakdown_with_charges_only()
    actions_taken = []

    for service, cost in service_costs.items():
        print(f"⚙️ Handling: {service} (${cost:.2f})")
        try:
            if call_handler_for_service(service):
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
 

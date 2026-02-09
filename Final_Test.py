
import boto3
import os
import sys
from botocore.exceptions import ClientError

# --- Configuration ---
TAG_KEY_CLI = 'CreatedBy'
TAG_VAL_CLI = 'platform-cli'
ALLOWED_TYPES = ['t3.micro', 't2.small']
MAX_EC2_CAP = 2
REGION = 'us-east-1'

# --- Initialize Clients ---
try:
    ec2_res = boto3.resource('ec2', region_name=REGION)
    s3_client = boto3.client('s3', region_name=REGION)
    ssm = boto3.client('ssm', region_name=REGION)
    r53 = boto3.client('route53')
except Exception as e:
    print(f"❌ AWS Connection Error: {e}")
    sys.exit(1)


# --- Shared Utilities ---
def get_latest_ami(choice):
    paths = {
        '1': '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64',
        '2': '/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id'
    }
    param = ssm.get_parameter(Name=paths[choice])
    return param['Parameter']['Value']


# --- EC2 Module ---
def manage_ec2():
    while True:
        print("\n--- 🖥️ EC2 Management ---")
        print("[1] Create Instance [2] List CLI Instances [3] Start/Stop [Q] Back")
        choice = input("Select: ").upper()
        if choice == '1':
            itype = input(f"Instance Type {ALLOWED_TYPES}: ").strip().lower()
            if itype not in ALLOWED_TYPES:
                print("❌ Invalid type.")
                continue
            running = list(ec2_res.instances.filter(Filters=[
                {'Name': f'tag:{TAG_KEY_CLI}', 'Values': [TAG_VAL_CLI]},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]))
            if len(running) >= MAX_EC2_CAP:
                print(f"❌ Cap reached ({len(running)}/{MAX_EC2_CAP} running).")
                continue
            print("OS: [1] Amazon Linux [2] Ubuntu")
            os_choice = input("Choice: ")
            if os_choice not in ['1', '2']: continue
            ami_id = get_latest_ami(os_choice)
            instance = ec2_res.create_instances(
                ImageId=ami_id, InstanceType=itype, MinCount=1, MaxCount=1,
                TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': TAG_KEY_CLI, 'Value': TAG_VAL_CLI}]}]
            )
            print(f"✅ Created {instance[0].id}")
        elif choice == '2':
            instances = ec2_res.instances.filter(Filters=[{'Name': f'tag:{TAG_KEY_CLI}', 'Values': [TAG_VAL_CLI]}])
            for i in instances:
                print(f"- {i.id} ({i.instance_type}) [{i.state['Name']}]")
        elif choice == '3':
            instances = list(
                ec2_res.instances.filter(Filters=[{'Name': f'tag:{TAG_KEY_CLI}', 'Values': [TAG_VAL_CLI]}]))
            if not instances:
                print("No CLI instances found.");
                continue
            for idx, inst in enumerate(instances):
                print(f"[{idx}] {inst.id} ({inst.state['Name']})")
            try:
                target = instances[int(input("Select index: "))]
                if target.state['Name'] == 'running':
                    target.stop()
                    print(f"🛑 Stopping {target.id}...")
                else:
                    target.start()
                    print(f"🏁 Starting {target.id}...")
            except:
                print("❌ Invalid choice.")
        elif choice == 'Q':
            break


# --- S3 Module ---
def get_cli_buckets():
    cli_buckets = []
    all_buckets = s3_client.list_buckets().get('Buckets', [])
    for b in all_buckets:
        try:
            tags = s3_client.get_bucket_tagging(Bucket=b['Name'])
            if any(t['Key'] == TAG_KEY_CLI and t['Value'] == TAG_VAL_CLI for t in tags['TagSet']):
                cli_buckets.append(b['Name'])
        except ClientError:
            continue
    return cli_buckets


def manage_s3():
    while True:
        print("\n--- 🪣 S3 Management ---")
        print("[1] Create Bucket [2] Upload File [3] List Buckets [Q] Back")
        choice = input("Select: ").upper()
        if choice == '1':
            name = input("Bucket Name: ").strip()
            is_public = input("Public? (y/n): ").lower() == 'y'
            if is_public and input("⚠️ Confirm public? (yes/no): ").lower() != 'yes': continue
            try:
                s3_client.create_bucket(Bucket=name)
                s3_client.put_bucket_tagging(Bucket=name,
                                             Tagging={'TagSet': [{'Key': TAG_KEY_CLI, 'Value': TAG_VAL_CLI}]})
                print(f"✅ Created {name}")
            except ClientError as e:
                print(f"❌ Error: {e.response['Error']['Message']}")
        elif choice == '2':
            buckets = get_cli_buckets()
            if not buckets: print("No CLI buckets."); continue
            target = input(f"Target Bucket {buckets}: ")
            if target not in buckets: print("❌ Not a CLI bucket."); continue
            path = input("File Path: ").strip()
            if os.path.exists(path):
                s3_client.upload_file(path, target, os.path.basename(path))
                print("✅ Uploaded.")
            else:
                print("❌ File not found.")
        elif choice == '3':
            for b in get_cli_buckets(): print(f"- {b}")
        elif choice == 'Q':
            break


# --- Route 53 Module ---
def get_cli_zones():
    cli_zones = []
    response = r53.list_hosted_zones()
    for zone in response['HostedZones']:
        zid = zone['Id'].split('/')[-1]
        try:
            tags = r53.list_tags_for_resource(ResourceType='hostedzone', ResourceId=zid)
            if any(t['Key'] == TAG_KEY_CLI and t['Value'] == TAG_VAL_CLI for t in tags['ResourceTagSet']['Tags']):
                cli_zones.append({'Name': zone['Name'], 'Id': zid})
        except:
            continue
    return cli_zones


def manage_route53():
    while True:
        print("\n--- 🌐 Route 53 Management ---")
        print("[1] Create Zone [2] Create/Update Record [3] Delete Record [4] List Zones [Q] Back")
        choice = input("Select: ").upper()

        if choice == '1':
            domain = input("Domain: ").strip()
            try:
                res = r53.create_hosted_zone(Name=domain, CallerReference=str(os.urandom(4).hex()))
                zid = res['HostedZone']['Id'].split('/')[-1]
                r53.change_tags_for_resource(ResourceType='hostedzone', ResourceId=zid,
                                             AddTags=[{'Key': TAG_KEY_CLI, 'Value': TAG_VAL_CLI}])
                print(f"✅ Created {domain}")
            except ClientError as e:
                print(f"❌ Error: {e.response['Error']['Message']}")

        elif choice == '2':  # Create/Update
            zones = get_cli_zones()
            if not zones: print("No CLI zones."); continue
            for idx, z in enumerate(zones): print(f"[{idx}] {z['Name']}")
            try:
                target = zones[int(input("Select Zone Index: "))]
                name = input("Record Name (e.g. app.domain.com): ").strip()
                rtype = input("Type (A, CNAME, TXT): ").upper()
                val = input("New Value (IP/Domain): ").strip()
                r53.change_resource_record_sets(
                    HostedZoneId=target['Id'],
                    ChangeBatch={'Changes': [{'Action': 'UPSERT',
                                              'ResourceRecordSet': {'Name': name, 'Type': rtype, 'TTL': 300,
                                                                    'ResourceRecords': [{'Value': val}]}}]}
                )
                print(f"✅ Record {name} upserted.")
            except Exception as e:
                print(f"❌ Error: {e}")

        elif choice == '3':  # SMART DELETE
            zones = get_cli_zones()
            if not zones: print("No CLI zones."); continue
            for idx, z in enumerate(zones): print(f"[{idx}] {z['Name']}")
            try:
                target = zones[int(input("Select Zone Index: "))]
                name = input("Record Name to delete: ").strip()
                if not name.endswith('.'): name += '.'

                # Fetch exact record set for matching
                records = r53.list_resource_record_sets(HostedZoneId=target['Id'], StartRecordName=name, MaxItems='1')
                match = records['ResourceRecordSets'][0]

                if match['Name'] != name:
                    print("❌ Exact record not found.");
                    continue

                r53.change_resource_record_sets(
                    HostedZoneId=target['Id'],
                    ChangeBatch={'Changes': [{'Action': 'DELETE', 'ResourceRecordSet': match}]}
                )
                print(f"✅ Record {name} deleted.")
            except Exception as e:
                print(f"❌ Error: {e}")

        elif choice == '4':
            for z in get_cli_zones(): print(f"- {z['Name']} ({z['Id']})")
        elif choice == 'Q':
            break


# --- Main Entry ---
def main():
    while True:
        print("\n--- 🚀 Platform CLI 2026 ---")
        service = input("Choose Service [ec2 / s3 / route53 / quit]: ").lower()
        if service == 'ec2':
            manage_ec2()
        elif service == 's3':
            manage_s3()
        elif service == 'route53':
            manage_route53()
        elif service == 'quit':
            break


if __name__ == "__main__":
    main()

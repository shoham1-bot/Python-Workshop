# Python-Workshop
Python intergrative AWS project

# AWS Platform CLI 

A security-first Python CLI tool to manage AWS resources (EC2, S3, Route53) with built-in cost constraints and tagging enforcement.

## What it Does
- EC2: Launches only `t3.micro` or `t2.small` instances with a hard cap of 2 running instances.
- S3: Manages buckets with explicit confirmation for public access.
- Route53: Creates and manages DNS records in CLI-managed hosted zones.

## Prerequisites
- Python: 3.8 or higher.
- AWS Permissions: An IAM user/role with EC2, S3, and Route53 full access.
- AWS Profile: Run `aws configure` to set your credentials locally.

## Installation
1. Clone the repository.
2. Install dependencies:
   pip install -r requirements.txt


Usage Examples
EC2: python platform_cli.py ec2

S3: python platform_cli.py s3

Route53: python platform_cli.py route53


Tagging Convention
Every resource created by this tool is automatically tagged with:

CreatedBy: platform-cli

Owner: (Extracted from your AWS IAM User)


Cleanup Instructions
To avoid AWS costs:

Use the EC2 menu to stop/terminate instances.

Use the S3 menu to list and then manually delete buckets via the AWS Console (or add a delete function).

Ensure Route53 Hosted Zones are deleted when no longer needed.


Working CLI & Security
My script already handles the core constraints and security:
* **Constraints:** It blocks instance types other than `t3.micro`/`t2.small` and enforces the 2-instance running cap.
* **Security:** By using `boto3.resource()` without hardcoding keys, it forces the use of **AWS Profiles** or **Roles**, preventing secrets from leaking into your Git history.
* **Tagging:** It validates the `CreatedBy` tag before allowing any "Start/Stop" or "Record Management" actions.


Demo Evidence
For your submission, run these commands and copy the output into a file named `DEMO.md` or as an appendix in your README:

1.  **EC2 Create:** Run `py platform_cli.py`, choose `ec2`, then `create`. Screenshot the "✅ Created" message.
2.  **S3 List:** Choose `s3`, then `list`. Show it only lists your CLI buckets.
3.  **Route53 Delete:** Show the "✅ Record deleted" message using the "Lookup-Before-Delete" logic we built.

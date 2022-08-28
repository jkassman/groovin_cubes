import json
import boto3
import io
import mimetypes
import os
import time
import zipfile

# avoid:
# botocore.errorfactory.ResourceConflictException:
#   An error occurred (ResourceConflictException) when calling the
#   UpdateFunctionCode operation: The operation cannot be performed at this time.
#   An update is in progress for resource: <arn_of_resource>
BLIND_CONFIG_WAIT_TIME = 1.5

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--force_updates', action="store_true")
args = parser.parse_args()


rest_api_id = "zllbrt4p87"
api_name = "killerfrog-api-demo"

api_gateway_json = {
    "swagger": "2.0",
    "info": {
        "version": "2018-07-21T19:28:58Z", # TODO Investigate
        "title": api_name
    },
    "host": f"{rest_api_id}.execute-api.us-east-2.amazonaws.com",
    "basePath": "/dev",
    "schemes": [
        "https"
    ],
}

invalid_file_top_message = (
"""file %s has an invalid file top!\n\n%s
All python files should start with:
# API_GATEWAY <gateway_id>
# <METHOD> </path>
# LAMBDA <lambda_name>
"""
)

files = os.listdir()
paths = []
for filename in files:
    if os.path.isfile(filename) and filename.endswith(".py") and filename != "deploy.py":
        line_top = ""
        with open(filename) as f:
            for i, line in enumerate(f):
                line_top += line
                if i >= 2:
                    break
        path = {"file": filename}
        for i, line in enumerate(line_top.split("\n")):
            if i >= 3:
                break
            split_line = line.split()
            assert split_line[0] == "#", invalid_file_top_message % (filename, line_top)
            if i == 0:
                assert split_line[1] == "API_GATEWAY", invalid_file_top_message % (filename, line_top)
                path["api_gateway"] = split_line[2]
            elif i == 1:
                path["method"] = split_line[1]
                path["path"] = split_line[2]
            if i == 2:
                assert split_line[1] == "LAMBDA", invalid_file_top_message % (filename, line_top)
                path["lambda"] = split_line[2]
        paths.append(path)

print(json.dumps(paths, indent=4))

gateway_paths = {}
for path in paths:
    method = path["method"]
    gateway_paths[path["path"]] = {
        method.lower(): {
            "produces": [
                "application/json"
            ],
            "x-amazon-apigateway-integration": {
                "uri": (
                    f"arn:aws:apigateway:us-east-2:lambda:path/2015-03-31/functions/"
                    f"arn:aws:lambda:us-east-2:539164448633:function:"
                    f"{path['lambda']}/invocations"
                ),
                "passthroughBehavior": "when_no_match",
                "httpMethod": "POST", # Note, POST required even for get
                "contentHandling": "CONVERT_TO_TEXT",
                "type": "aws_proxy"
            }
        }
    }
api_gateway_json["paths"] = gateway_paths


def deploy_api_gateway(api_gateway_json):
    api_gateway = boto3.client("apigateway")
    api_gateway.put_rest_api(
        restApiId=rest_api_id,
        mode='overwrite',
        failOnWarnings=True,
        body=json.dumps(api_gateway_json)
    )

    api_gateway.create_deployment(
        restApiId=rest_api_id,
        stageName='dev',
        #stageDescription='string',
        #description='string',
    )
if paths:
    deploy_api_gateway(api_gateway_json)

def create_lambda(client, lambda_name, lambda_file, api_source_arn):
    iam_role = "midway_lambda" # TODO customize this
    zipped_bytes = io.BytesIO()
    with zipfile.ZipFile(zipped_bytes, "w") as z:
        z.write(lambda_file)

    config = dict(
        FunctionName=lambda_name,
        Role=f"arn:aws:iam::539164448633:role/{iam_role}",
        Handler=f'{os.path.splitext(lambda_file)[0]}.lambda_handler',
        #Description='string',
        #Timeout=123,
        #MemorySize=123,
      )
    try:
      client.create_function(
        Runtime='python3.9',
        Code={"ZipFile": zipped_bytes.getvalue()},
        **config,
      )
    except client.exceptions.ResourceConflictException:
        if args.force_updates:
            client.update_function_configuration(**config)
            time.sleep(BLIND_CONFIG_WAIT_TIME)
        client.update_function_code(
            FunctionName=lambda_name,
            ZipFile=zipped_bytes.getvalue()
        )
    if args.force_updates:
        statement_id = f'{lambda_name}-policy'
        try:
            client.remove_permission(
                FunctionName=lambda_name,
                StatementId=statement_id,
                #Qualifier='string',
                #RevisionId='string'
            )
        except client.exceptions.ResourceNotFoundException:
            pass
        time.sleep(BLIND_CONFIG_WAIT_TIME)
        client.add_permission(
            FunctionName=lambda_name,
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=api_source_arn
            #SourceAccount='string',
            #EventSourceToken='string',
            #Qualifier='string',
            #RevisionId='string',
            #PrincipalOrgID='string',
            #FunctionUrlAuthType='NONE'|'AWS_IAM'
        )


lambda_client = boto3.client("lambda")

for path in paths:
    api_source_arn =  (
        f"arn:aws:execute-api:us-east-2:539164448633:{rest_api_id}"
        f"/*/{path['method'].upper()}{path['path']}"
    )
    create_lambda(lambda_client, path["lambda"], path["file"], api_source_arn)

def deploy_s3_files():
    s3 = boto3.client("s3")
    home_page = ""
    with open("s3_list.txt") as f:
        for i, line in enumerate(f):
            split_line = line.split()
            if i == 0:
                assert split_line[0] == "S3_BUCKET:"
                bucket_name = split_line[1]
            else:
                if len(split_line) == 2:
                    assert split_line[1] == "#HOMEPAGE"
                    home_page = split_line[0]
                else:
                    assert len(split_line) == 1, split_line
                file_name_to_upload = split_line[0]
                s3.upload_file(
                    file_name_to_upload, bucket_name, file_name_to_upload,
                    ExtraArgs={
                        "ACL":"public-read",
                        "ContentType": mimetypes.guess_type(file_name_to_upload)[0]
                    }
                )

    print(f"https://{bucket_name}.s3.us-east-2.amazonaws.com/{home_page}")

#deploy_s3_files()

# Copyright 2016 Amazon.com, Inc. or its affiliates.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#    http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file.
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

import re
import json
import boto3
import zipfile
import cStringIO
from botocore.client import Config


def boto3_agent_from_sts(agent_service, agent_type, region, credentials={}):
    session = boto3.session.Session()

    # Generate our kwargs to pass
    kw_args = {
        "region_name": region,
        "config": Config(signature_version='s3v4')
    }

    if credentials:
        kw_args["aws_access_key_id"] = credentials['accessKeyId']
        kw_args["aws_secret_access_key"] = credentials['secretAccessKey']
        kw_args["aws_session_token"] = credentials['sessionToken']

    # Build our agent depending on how we're called.
    if agent_type == "client":
        return (session.client(
            agent_service,
            **kw_args
        ))
    if agent_type == "resource":
        return (session.resource(
            agent_service,
            **kw_args
        ))


def determine_region(context):
    m = re.match("arn:aws:lambda:(.*?):\d+.*$", context.invoked_function_arn)
    if m:
        return (m.group(1))
    else:
        raise RuntimeError(
            "Could not determine region from arn {}".format(
                context.invoked_function_arn
            )
        )


def determine_account_id(context):
    m = re.match("arn:aws:lambda:.*?:(\d+).*$", context.invoked_function_arn)
    if m:
        return (m.group(1))
    else:
        raise RuntimeError(
            "Could not determine account id from arn {}".format(
                context.invoked_function_arn
            )
        )


def check_automation_success(client, AutomationExecutionId):
    wait_codes = ["Pending", "InProgress", "Waiting"]
    fail_codes = ["TimedOut", "Cancelled", "Failed"]
    success_codes = ["Success"]

    fullresponse = client.get_automation_execution(
        AutomationExecutionId=AutomationExecutionId
    )
    response = fullresponse['AutomationExecution']

    if response['AutomationExecutionStatus'] in wait_codes:
        print "Waiting for automation {} to finish . . .".format(
            AutomationExecutionId
        )
        return (False)

    if response['AutomationExecutionStatus'] in fail_codes:
        raise RuntimeError(
            "Automation ID {} has failed: {}".format(
                AutomationExecutionId,
                response['FailureMessage']
            )
        )

    if response['AutomationExecutionStatus'] in success_codes:
        return (True)

    return (False)


def parse_automation_outputs(client, AutomationExecutionId):
    fullresponse = client.get_automation_execution(
        AutomationExecutionId=AutomationExecutionId
    )
    response = fullresponse['AutomationExecution']

    total_tasks = 0
    completed_tasks = 0

    automation_outputs = {}
    for StepExecution in response['StepExecutions']:
        total_tasks += 1
        print "Automation Step: {} is in state: {}".format(
            StepExecution['StepName'],
            StepExecution['StepStatus']
        )
        if StepExecution['StepStatus'] == "Success":
            completed_tasks += 1
        StepName = StepExecution['StepName']
        if "Outputs" in StepExecution:
            automation_outputs[StepName] = StepExecution['Outputs']

    automation_outputs['_percent_complete'] = int(
        float(completed_tasks) / float(total_tasks) * 100
    )

    return (automation_outputs)


def launch_install_software(event, config, local_account, client):
    input_artifact = event['CodePipeline.job']['data']['inputArtifacts'][0]
    artifact_location = input_artifact['location']['s3Location']

    automation_document = config['SSMAutomation']['SSMDocuments']['LaunchAndInstall']
    automation_parameters = {
        "SourceAmiId": [config['SSMAutomation']['Instance']['SourceAmiId']],
        "InstanceIamRole": [config['SSMAutomation']['Instance']['InstanceProfile']],
        "AutomationAssumeRole": [config['SSMAutomation']['AutomationRole']],
        "InstanceType": [config['SSMAutomation']['Instance']['InstanceType']],
        "SubnetId": [config['SSMAutomation']['Instance']['SubnetId']],
        "InstanceNameTag": [config['SSMAutomation']['Instance']['NameTag']],
        "GitRepoName": [config['CodeCommit']['RepoName']],
        'GitCloneURL': [config['CodeCommit']['CloneURL']],
        'InstallScript': [config['SSMAutomation']['Instance']['InstallScript']],
        'BuildArtifactBucket': [artifact_location['bucketName']],
        'BuildArtifactKey': [artifact_location['objectKey']],
        'InstallInspector': [config['InstallInspectorAgent']]
    }

    response = client.start_automation_execution(
        DocumentName=automation_document,
        Parameters=automation_parameters
    )

    AutomationExecutionId = response['AutomationExecutionId']

    return (AutomationExecutionId)


def launch_ami_build(event, build_state, local_account, client):
    config = build_state['config']

    automation_document = config['SSMAutomation']['SSMDocuments']['TerminateAndBake']
    automation_parameters = {
        "AutomationAssumeRole": [config['SSMAutomation']['AutomationRole']],
        "SourceAmiId": [config['SSMAutomation']['Instance']['SourceAmiId']],
        "RunningInstanceID": [
            build_state['automation_outputs']['install_software']['launchInstance']['InstanceIds'][0]],
        "CreateAMI": [config['InstallInspectorAgent']]
    }

    response = client.start_automation_execution(
        DocumentName=automation_document,
        Parameters=automation_parameters
    )

    AutomationExecutionId = response['AutomationExecutionId']

    return (AutomationExecutionId)


def extract_config_or_buildstate(event, client):
    input_artifact = event['CodePipeline.job']['data']['inputArtifacts'][0]
    artifact_location = input_artifact['location']['s3Location']

    client.download_file(
        artifact_location['bucketName'],
        artifact_location['objectKey'],
        '/tmp/artifact.zip'
    )

    zf = zipfile.ZipFile('/tmp/artifact.zip')

    # Preference for a build_state.json if it exists.
    for filename in zf.namelist():
        if filename == "build_state.json":
            print "Found a build_state.json file in artifact"
            return (json.loads(zf.read(filename)))

    # Secondary preference for a config.json
    for filename in zf.namelist():
        if filename == "config.json":
            print "Found a config.json file in artifact"
            return (json.loads(zf.read(filename)))

    # Can't proceed without either of them.
    raise RuntimeError("Unable to find config.json in build artifact output")


def save_buildstate_as_artifact(event, client, build_state):
    output_artifact = event['CodePipeline.job']['data']['outputArtifacts'][0]
    artifact_location = output_artifact['location']['s3Location']

    build_state_fh = cStringIO.StringIO()
    build_state_fh.write(json.dumps(build_state))

    zf = zipfile.ZipFile('/tmp/artifact.zip', mode='a')
    zf.writestr("build_state.json", build_state_fh.getvalue())
    zf.close()

    fh = open("/tmp/artifact.zip", "r")
    client.put_object(
        Bucket=artifact_location['bucketName'],
        Key=artifact_location['objectKey'],
        ServerSideEncryption="aws:kms",
        Body=fh
    )

    print "Saving build_state to artifact: {}".format(
        json.dumps(build_state)
    )


def lambda_handler(event, context):
    print "Raw event: {}".format(
        json.dumps(event)
    )

    local_account = determine_account_id(context)
    local_region = determine_region(context)

    # CodePipeline agent so we can send an exception.
    cp_c = boto3_agent_from_sts("codepipeline", "client", local_region)

    try:
        # Extract our credentials and locate our artifact from our build.
        credentials = event['CodePipeline.job']['data']['artifactCredentials']
        artifact_s3_c = boto3_agent_from_sts(
            "s3",
            "client",
            local_region,
            credentials
        )

        # SSM Credentials from our Lambda function
        ssm_c = boto3_agent_from_sts(
            "ssm",
            "client",
            local_region
        )

        config = {}
        build_state = {}
        artifact_config = extract_config_or_buildstate(event, artifact_s3_c)
        if artifact_config.get('config'):
            build_state = artifact_config
            print "build_state: {}".format(
                json.dumps(build_state)
            )
            config = build_state['config']
            build_phase = "ami_build"
        else:
            config = artifact_config
            print "config: {}".format(
                json.dumps(config)
            )
            build_phase = "install_software"

        AutomationExecutionId = ""
        # Find out if we're in a continuation or not.
        if "continuationToken" in event['CodePipeline.job']['data']:
            continuationToken = json.loads(
                event['CodePipeline.job']['data']['continuationToken']
            )
            AutomationExecutionId = continuationToken['AutomationExecutionId']
        else:
            # Not in a continuation.  Launch our respective automation document.
            if build_phase == "ami_build":
                AutomationExecutionId = launch_ami_build(
                    event, build_state, local_account, ssm_c)
            elif build_phase == "install_software":
                s3_c = boto3_agent_from_sts(
                    "s3",
                    "client",
                    local_region
                )
                # write_customization_script(event, config, artifact_s3_c, s3_c)
                AutomationExecutionId = launch_install_software(
                    event, config, local_account, ssm_c)

            print "Launched automation as id: {}".format(
                AutomationExecutionId
            )

        # Check if our automation is finished.
        result = check_automation_success(
            ssm_c,
            AutomationExecutionId
        )

        # Read our outputs for our artifacts / percentage complete.
        automation_outputs = parse_automation_outputs(
            ssm_c,
            AutomationExecutionId
        )

        # Build our kwargs for codepipline job result.
        job_result_kwargs = {
            "jobId": event['CodePipeline.job']['id']
        }

        if result is True:
            # populate our build_state so we can save it for the next step.
            build_state['config'] = config
            if build_state.get('automation_outputs'):
                build_state['automation_outputs']['build_phase'] = automation_outputs
            else:
                build_state['automation_outputs'] = {
                    build_phase: automation_outputs
                }
            if build_state.get('AutomationExecutionId'):
                build_state['AutomationExecutionId'][build_phase] = AutomationExecutionId
            else:
                build_state['AutomationExecutionId'] = {
                    build_phase: AutomationExecutionId
                }
            save_buildstate_as_artifact(
                event,
                artifact_s3_c,
                build_state
            )
            job_result_kwargs['executionDetails'] = {
                'summary': "Successfully ran automation document",
                'percentComplete': 100
            }
            print "Successfully ran automation document"
        else:
            # we need to continue waiting send a continuation token
            job_result_kwargs['executionDetails'] = {
                'summary': "Waiting for Automation Job to complete",
                'percentComplete': automation_outputs['_percent_complete']
            }
            job_result_kwargs['continuationToken'] = json.dumps(
                {
                    "job_id": event['CodePipeline.job']['id'],
                    "AutomationExecutionId": AutomationExecutionId
                }
            )
            print "Automation build is {}% complete".format(
                automation_outputs['_percent_complete']
            )

        # Put our result in
        cp_c.put_job_success_result(
            **job_result_kwargs
        )

    except Exception as e:
        # On exception we will termiante our pipeline.
        cp_c.put_job_failure_result(
            jobId=event['CodePipeline.job']['id'],
            failureDetails={
                'type': 'JobFailed',
                'message': 'Exception: {}'.format(e)
            }
        )
        raise

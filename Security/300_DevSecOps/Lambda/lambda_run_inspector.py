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


def inspector_run_assessment(build_state, client):
    config = build_state['config']

    response = client.start_assessment_run(
        assessmentTemplateArn=config['InspectorTemplateArn']
    )

    return response['assessmentRunArn']


def inspector_run_state(client, assessment_run_arn):
    response = client.describe_assessment_runs(
        assessmentRunArns=[
            assessment_run_arn,
        ]
    )

    success_states = [
        'COMPLETED'
    ]

    error_states = [
        'FAILED',
        'ERROR',
        'COMPLETED_WITH_ERRORS',
        'CANCELED'
    ]

    if response['assessmentRuns'][0]['state'] in success_states:
        return 'success'
    elif response['assessmentRuns'][0]['state'] in error_states:
        return 'failed'
    else:
        return "inprogress"


def gather_finding_results(build_state, client, assessment_run_arn):
    instance_id = build_state['automation_outputs']['install_software']['launchInstance']['InstanceIds'][0]

    # AgentId is our instance ID, and severities set to high means we can do a simple count on return
    response = client.list_findings(
        assessmentRunArns=[
            assessment_run_arn
        ],
        filter={
            "severities": [
                'High'
            ],
            "agentIds": [
                instance_id
            ]
        }
    )

    return len(response['findingArns'])


def terminate_instance(event, build_state, local_account, client):
    config = build_state['config']

    automation_document = config['SSMAutomation']['SSMDocuments']['TerminateAndBake']
    automation_parameters = {
        "AutomationAssumeRole": [config['SSMAutomation']['AutomationRole']],
        "SourceAmiId": [config['SSMAutomation']['Instance']['SourceAmiId']],
        "RunningInstanceID": [
            build_state['automation_outputs']['install_software']['launchInstance']['InstanceIds'][0]],
        "CreateAMI": ['false']
    }

    response = client.start_automation_execution(
        DocumentName=automation_document,
        Parameters=automation_parameters
    )

    print "Terminating instance due to failed build.  Kicked off automation execution id {}".format(
        response['AutomationExecutionId'])


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


def read_artifact_as_state(event, client):
    input_artifact = event['CodePipeline.job']['data']['inputArtifacts'][0]
    artifact_location = input_artifact['location']['s3Location']

    response = client.get_object(
        Bucket=artifact_location['bucketName'],
        Key=artifact_location['objectKey'],
    )

    if response.get('Body'):
        build_state = response['Body'].read()

    return (json.loads(build_state))


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

        # Inspector credentials from the Lambda function.
        inspector_c = boto3_agent_from_sts(
            "inspector",
            "client",
            local_region
        )

        build_state = extract_config_or_buildstate(event, artifact_s3_c)
        print "Build state loaded: {}".format(
            json.dumps(build_state)
        )

        ssm_c = boto3_agent_from_sts(
            "ssm",
            "client",
            local_region
        )

        # Make sure we can find our instance ID in our job state.
        if not build_state.get('automation_outputs').get('install_software'):
            raise RuntimeError(
                "Unable to find an instance ID in the input.  Assure the input to this stage is the output from the laumch and install software stage!")

        assessment_run_arn = ""
        # Find out if we're in a continuation or not.
        if "continuationToken" in event['CodePipeline.job']['data']:

            continuationToken = json.loads(
                event['CodePipeline.job']['data']['continuationToken']
            )
            assessment_run_arn = continuationToken['assessment_run_arn']
        else:
            # Not in a continuation.  Execute our scan
            # Catch a failure that the agent isn't installed during the run.
            try:
                assessment_run_arn = inspector_run_assessment(
                    build_state, inspector_c)
            except Exception as e:
                terminate_instance(event, build_state, local_account, ssm_c)
                raise RuntimeError(
                    "No targets found for the inspector scan.  Make sure you have installed the inspector agent!")

        # Check if our automation is finished.
        run_state = inspector_run_state(
            inspector_c,
            assessment_run_arn
        )

        # Build our kwargs for codepipline job result.
        job_result_kwargs = {
            "jobId": event['CodePipeline.job']['id']
        }

        if run_state == "failed":
            # Terminate our instance so it isn't orphaned.
            terminate_instance(event, build_state, local_account, ssm_c)
            raise RuntimeError(
                "Inspector Run: {} Failed.  Check inspector console.  Check for orphaned instances from failed runs!".format(
                    assessment_run_arn))
        if run_state == "success":

            finding_count = gather_finding_results(
                build_state, inspector_c, assessment_run_arn)
            build_state['inspector'] = {
                "finding_count": finding_count
            }
            save_buildstate_as_artifact(
                event,
                artifact_s3_c,
                build_state
            )

            if finding_count == 0:
                # Run our job on our instance to mark that it passed this stage!
                # we won't confirm our output went successfully so we don't extend our pipeline any longer than needed.
                ssm_c.send_command(
                    InstanceIds=[
                        build_state['automation_outputs']['install_software']['launchInstance']['InstanceIds'][0]
                    ],
                    DocumentName="AWS-RunShellScript",
                    Parameters={
                        "commands": [
                            "cp /var/www/html/inspector-done.json /var/www/html/inspector.json"
                        ]
                    }
                )
                job_result_kwargs['executionDetails'] = {
                    'summary': "Successfully ran automation document",
                    'percentComplete': 100
                }
            else:
                # Terminate our instance so it isn't orphaned.
                terminate_instance(event, build_state, local_account, ssm_c)
                raise RuntimeError(
                    "Instance failed inspection.  {} High severity vulnerabilities found.  See the 'Amazon Inspector' console for details".format(
                        finding_count))
        else:
            # Job hasn't finished, send a continuation token
            # we need to continue waiting send a continuation token
            job_result_kwargs['executionDetails'] = {
                'summary': "Waiting for Inspector Run to complete",
                'percentComplete': 0
            }
            job_result_kwargs['continuationToken'] = json.dumps(
                {
                    "job_id": event['CodePipeline.job']['id'],
                    "assessment_run_arn": assessment_run_arn
                }
            )
            print "Inspector run {} is not yet complete".format(assessment_run_arn)

        # Put our result in
        cp_c.put_job_success_result(
            **job_result_kwargs
        )

    except RuntimeError as e:
        cp_c.put_job_failure_result(
            jobId=event['CodePipeline.job']['id'],
            failureDetails={
                'type': 'JobFailed',
                'message': 'Exception: {}'.format(e)
            }
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

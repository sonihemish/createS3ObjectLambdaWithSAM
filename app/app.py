# S3 Object Lambda to reads CSV and convert it to JSON.
import json
import csv
import boto3
import urllib3


def handler(event, context):
    # Output the event to the logs for debugging
    print(event)

    # Get Operation Context from event
    operation_context = event["getObjectContext"]

    # Retrieve the Operation context and the outputRoute, outputToken and inputS3Url from the context
    output_route = operation_context["outputRoute"]
    output_token = operation_context["outputToken"]
    input_s3_url = operation_context["inputS3Url"]
    http = urllib3.PoolManager()
    response = http.request('GET',
                            input_s3_url)

    # Get object from S3
    original_object = response.data

    # Convert the CSV to JSON
    json_object = json.dumps(list(csv.DictReader(original_object.decode('utf-8').splitlines())))

    print(json_object)
    s3 = boto3.client('s3')
    s3.write_get_object_response(
        Body=json_object,
        RequestRoute=output_route,
        RequestToken=output_token)

    return {
        'statusCode': 200,
        'body': json.dumps(json_object)
    }
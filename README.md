## Introduction

This guide helps the user create a S3 Object Lambda using AWS SAM
## About SAM

The AWS Serverless Application Model (SAM) is an open-source framework for building serverless applications. It provides shorthand syntax to express functions, APIs, databases, and event source mappings. With just a few lines per resource, you can define the application you want and model it using YAML. During deployment, SAM transforms and expands the SAM syntax into AWS CloudFormation syntax, enabling you to build serverless applications faster.
## About S3 Object Lambda

With S3 Object Lambda, you can add your own code to S3 GET, HEAD, and LIST requests to modify and process data as it is returned to an application. You can use custom code to modify the data returned by S3 GET requests to filter rows, dynamically resize images, redact confidential data, and much more. You can also use S3 Object Lambda to modify the output of S3 LIST requests to create a custom view of objects in a bucket and S3 HEAD requests to modify object metadata like object name and size. Powered by AWS Lambda functions, your code runs on infrastructure that is fully managed by AWS, eliminating the need to create and store derivative copies of your data or to run expensive proxies, all with no changes required to your applications.

## Prerequisites 

1. An AWS Account : If you do not have the account you can create one [here](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html)  and create a IAM user with sufficient permissions to make necessary AWS service calls and manage AWS resources.
2. Install and configure [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) 
3. Install [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
4. Install and configure [AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) 

## Source Code
The below written code can be found in the following git repository. If wish you can use this in stead of using the steps below. 
### Create a SAM template file (template.yaml) 

The following is the structure of the SAM template file which will allow you to create an S3 Object Lambda

You can use a quick start template to create the structure of the template.yaml file by using the following command. 

```
sam init
```

```

You can preselect a particular runtime or package type when using the `sam init` experience.
Call `sam init --help` to learn more.

Which template source would you like to use?
        1 - AWS Quick Start Templates
        2 - Custom Template Location
Choice: 1

Choose an AWS Quick Start application template
        1 - Hello World Example
        2 - Data processing
        3 - Hello World Example with Powertools for AWS Lambda
        4 - Multi-step workflow
        5 - Scheduled task
        .
        .
        .
        

Template: 1

Use the most popular runtime and package type? (Python and zip) [y/N]: y

Would you like to enable X-Ray tracing on the function(s) in your application?  [y/N]: n

Would you like to enable monitoring using CloudWatch Application Insights?
For more info, please view https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-application-insights.html [y/N]: y^?n

Project name [sam-app]: myapp

AWSTemplateFormatVersion: '2010-09-09'  
Transform: AWS::Serverless-2016-10-31  
Description: Exmple of creating a S3 Object Lambda with SAM template
```

Next change directory to app directory (in my case myapp)

```
cd myapp
```

Under the myapp folder you will see template.yaml
Use your choice of editor to update this file 

#### Create the Resource:  

Create all resources under the resources section: 
```
Resources:
```

Let us start by creating the S3 bucket which is the object is going to be places. Place this under the resource section of the template

```
S3Bucket:  
  Type: 'AWS::S3::Bucket'  
  Properties:  
    BucketEncryption:  
      ServerSideEncryptionConfiguration:  
        - ServerSideEncryptionByDefault:  
            SSEAlgorithm: AES256  
    PublicAccessBlockConfiguration:  
      BlockPublicAcls: true  
      BlockPublicPolicy: true  
      IgnorePublicAcls: true  
      RestrictPublicBuckets: true  
    VersioningConfiguration:  
      Status: Enabled
```

Next we create the S3 Bucket Policy attaching it to the bucket created above. Giving it the ability to access resources in AWS. This is required for the bucket objects to invoke the lambda. 

```
S3BucketPolicy:  
  Type: 'AWS::S3::BucketPolicy'  
  Properties:  
    Bucket: !Ref S3Bucket  
    PolicyDocument:  
      Version: 2012-10-17  
      Statement:  
        - Action: '*'  
          Effect: Allow  
          Resource:  
            - !GetAtt S3Bucket.Arn  
            - !Sub  
                - '${varS3BucketArn}/*'  
                - varS3BucketArn: !GetAtt S3Bucket.Arn  
          Principal:  
            AWS: '*'  
          Condition:  
            StringEquals:  
              's3:DataAccessPointAccount': !Sub ${AWS::AccountId}

```

In the above policy we have allowed the policy to have access to everything in the principal section, however a general best practices of least privilege should apply especially for production workload. 

Next we add the Lambda 

```
# Lambda function  
ObjectLambdaFunction:  
  Type: 'AWS::Serverless::Function'  
  Properties:  
    CodeUri: app/  
    Handler: app.handler  
    Runtime: python3.11  
    MemorySize: 1024  
    # The function needs permission to call back to the S3 Object Lambda Access Point with the WriteGetObjectResponse.  
    Policies:  
      - S3CrudPolicy:  
          BucketName: !Ref S3Bucket  
      - Statement:  
        - Effect: Allow  
          Action: 's3-object-lambda:WriteGetObjectResponse'  
          Resource: '*'
```

For the purpose of this example I have created a simple lambda Function that converts CSV file to JSON file. Place this under myapp/app folder as app.py

```
# S3 Object Lambda to reads CSV and convert it to JSON.  
import json  
import csv  
import boto3  
import urllib3  
  
def handler(event, context):  
    # Output the event to the logs for debugging  
    print(event)  
  
    #Get Operation Context from event  
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
```

Next we add the Access points first the S3 Access Point to the template.yaml file
```
# S3 Access Point (Network origin: Internet)  
S3AccessPoint:  
  Type: 'AWS::S3::AccessPoint'  
  Properties:  
    Bucket: !Ref S3Bucket  
    Name: 'myapp-ap'
    
```

Next we add the the lamba access point 

```
# S3 Object Lambda Access Point  
S3ObjectLambdaAccessPoint:  
  Type: 'AWS::S3ObjectLambda::AccessPoint'  
  Properties:  
    Name: 'myapp-olap'  
    ObjectLambdaConfiguration:  
        SupportingAccessPoint: !Sub 'arn:aws:s3:${AWS::Region}:${AWS::AccountId}:accesspoint/${S3AccessPoint}'  
        TransformationConfigurations:  
        - Actions:  
            - GetObject  
          ContentTransformation:  
            AwsLambda:  
              FunctionArn: !GetAtt ObjectLambdaFunction.Arn  
              FunctionPayload: 'test-payload'
```

Next we create the output section of the template

```
Outputs:  
  S3BucketName:  
    Value: !Ref S3Bucket  
    Description: S3 Bucket for object storage.  
  S3AccessPointArn:  
    Value: !Ref S3AccessPoint  
    Description: Name of the S3 access point.  
  S3ObjectLambdaAccessPointArn:  
    Value: !GetAtt S3ObjectLambdaAccessPoint.Arn  
    Description: ARN of the S3 Object Lambda access point.  
  LambdaFunctionArn:  
    Value: !Ref ObjectLambdaFunction  
    Description: ObjectLambdaFunction ARN.
```

sam build
sam deploy --guided 

The guided sam deployment command will as you a set of configuration before deployment. See below the example of the configuration I have use. You can tweet these according to your setup. 

```                                           
	sam deploy --guided 
	Configuring SAM deploy
	======================

	Looking for config file [samconfig.toml] :  Found
	Reading default arguments  :  Success

	Setting default arguments for 'sam deploy'
	=========================================
	Stack Name [myapp]:
	AWS Region [eu-west-2]:
	#Shows you resources changes to be deployed and require a 'Y' to initiate deploy
	Confirm changes before deploy [Y/n]: y
	#SAM needs permission to be able to create roles to connect to the resources in your template
	Allow SAM CLI IAM role creation [Y/n]: y
	#Preserves the state of previously provisioned resources when an operation fails
	Disable rollback [y/N]: n
	Save arguments to configuration file [Y/n]: y
	SAM configuration file [samconfig.toml]:
	SAM configuration environment [default]:

	Looking for resources needed for deployment:

```

Once sucessfully deploy you should be able to test the application
## Test

Let us now test the deployment 

create a test CVS file in the tests folder 
```
A,B,C
1,2,3
4,5,6
7,8,9
```

Upload the file to the S3 bucket
```
cd tests
aws s3 cp test1.csv s3://[your-bucket-name]
```


Now S3 Object Lambda using the access point. The accesspoint arn can be found in the output section of the cloud formation template
 
```
aws s3api get-object --bucket '[Object Lambda Access point]' --key test1.csv 'test1.json'
```

The json file is now created in the tests folder

```
[{"A": "1", "B": "2", "C": "3"}, {"A": "4", "B": "5", "C": "6"}, {"A": "7", "B": "8", "C": "9"}]
```

## Cleanup

It is important to cleanup the cloud resources you have created so that it does not require any cost associated with it and also as a measure of leaving any insecure implementations around. 

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```
sam delete --stack-name "myapp"
```

## Source Code

The source code for the following is available in github

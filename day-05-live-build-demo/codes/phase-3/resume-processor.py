import json
import boto3
import urllib.parse

textract = boto3.client('textract')

SNS_TOPIC_ARN = "SNS-TOPIC-ARN"
TEXTRACT_ROLE_ARN = "TEXTRACT-ROLE-ARN"

def lambda_handler(event, context):
    
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(record['s3']['object']['key'])
    
    print(f"Processing file: {key}")
    
    if not key.lower().endswith(".pdf"):
        print("Not a PDF. Skipping.")
        return
    
    response = textract.start_document_text_detection(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        NotificationChannel={
            'SNSTopicArn': SNS_TOPIC_ARN,
            'RoleArn': TEXTRACT_ROLE_ARN
        }
    )
    
    job_id = response['JobId']
    
    print(f"Textract job started: {job_id}")
    
    return {
        'statusCode': 200,
        'body': f"Job started: {job_id}"
    }
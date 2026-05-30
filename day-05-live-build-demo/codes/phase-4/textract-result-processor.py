import json
import boto3

textract = boto3.client('textract')

def lambda_handler(event, context):
    
    print("SNS EVENT RECEIVED:")
    print(json.dumps(event, indent=2))
    
    message = json.loads(event['Records'][0]['Sns']['Message'])
    
    job_id = message['JobId']
    status = message['Status']
    
    print(f"Job ID: {job_id}")
    print(f"Status: {status}")
    
    if status != "SUCCEEDED":
        print("Textract job failed")
        return
    
    extracted_text = []
    
    next_token = None
    
    while True:
        
        if next_token:
            response = textract.get_document_text_detection(
                JobId=job_id,
                NextToken=next_token
            )
        else:
            response = textract.get_document_text_detection(
                JobId=job_id
            )
        
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                extracted_text.append(item['Text'])
        
        # Check if more pages exist
        next_token = response.get('NextToken')
        
        if not next_token:
            break
    
    full_text = "\n".join(extracted_text)
    
    print("===== FINAL EXTRACTED TEXT =====")
    print(full_text)
    
    return {
        'statusCode': 200
    }

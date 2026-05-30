import json

def lambda_handler(event, context):
    print("EVENT RECEIVED:")
    print(json.dumps(event, indent=2))

    return {
        'statusCode': 200,
        'body': 'Lambda triggered successfully'
    }

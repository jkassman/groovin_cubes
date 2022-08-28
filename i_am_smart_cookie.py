# API_GATEWAY zllbrt4p87
# GET /I/am/smart/cookie
# LAMBDA cookie
import random
def lambda_handler(event, context):
    value = "c"
    for i in range(random.randint(1,67)):
        value += "o"
    value += "kie"
    status = 200
    if len(value) > 60:
        status = 500
        value = "too much of a good thing is a...bad thing"
    return {
        "isBase64Encoded": False,
        "statusCode": status,
        "headers": {
            'Content-Type': 'text/plain',
            'access-control-allow-origin': '*',
        },
        "body": value
    }

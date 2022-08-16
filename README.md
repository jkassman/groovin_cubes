# groovin_cubes
Cubes be Groov'n

The idea is to simplify building a web page / simplify api-gateway/lambda interactions.

**s3_list.txt**
```
S3_BUCKET <bucket_name>
whatever.html # HOMEPAGE
whatever.js
favicon.ico
```

**some_python_file.py**<br>
```
# API_GATEWAY {specific API gateway}
# /home/add_user
# LAMBDA <lambda_name>
# DYNAMO <table_name>
def lambda_handler(event, context):
    dynamo = boto3.client("dynamodb")
    q_params = event['queryStringParameters']
    game_id = q_params['game']
    user_id = q_params['player']
    # Get game state
    result =  dynamo.get_item(TableName='pointless_games',
                              Key={'game_id': {'S' : game_id}},
                              ConsistentRead=True)
```

TODO unittesting documentation

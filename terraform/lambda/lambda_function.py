import json
from urllib.parse import unquote_plus
import boto3
import os
import logging

print("Loading function")
logger = logging.getLogger()
logger.setLevel("INFO")
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
reckognition = boto3.client("rekognition")

table = dynamodb.Table(os.getenv("DYNAMO_TABLE"))
def lambda_handler(event, context):
    logger.info(json.dumps(event, indent=2))
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = unquote_plus(event["Records"][0]["s3"]["object"]["key"])

    # Récupération de l'utilisateur et de l'UUID de la tâche
    user_tag, task_uuid = key.split("/")[:2]

    # Ajout des tags user et task_uuid
    user = "USER#" + user_tag
    task_id = "POST#" + task_uuid

    label_data = reckognition.detect_labels(
        Image={"S3Object": {"Bucket": bucket, "Name": key}},
        MaxLabels=5,
        MinConfidence=0.80,
    )
    logger.info(f"Labels data : {label_data}")

    # Récupération des résultats des labels
    labels = [label["Name"] for label in label_data["Labels"]]
    logger.info(f"Labels detected : {labels}")

    table.update_item(
        Key={"user": user_tag, "id": task_uuid},
        UpdateExpression="SET labels = :labels",
        ExpressionAttributeValues={":labels": labels},
    )

    url = s3.generate_presigned_url(
        Params={
            "Bucket": bucket,
            "Key": key,
        },
        ClientMethod="get_object",
    )

    table.update_item(
        Key={"user": user, "id": task_id},
        UpdateExpression="SET image = :url",
        ExpressionAttributeValues={":url": url},
    )

import json
import uuid
from unittest import mock

from mypy_boto3_sqs.service_resource import Message as SQSMessage

from taskhawk.models import Message


def build_aws_sqs_message(message: Message) -> SQSMessage:
    sqs_message = mock.create_autospec(SQSMessage)
    sqs_message.body = json.dumps(message.as_dict())
    sqs_message.message_attributes = {
        k: {"StringValue": str(v), "DataType": "String"} for k, v in message.as_dict()['headers'].items()
    }
    sqs_message.receipt_handle = message.provider_metadata.receipt
    return sqs_message


def build_aws_sns_record(message: Message) -> dict:
    # copied from https://docs.aws.amazon.com/lambda/latest/dg/with-sns.html
    return {
        "EventVersion": "1.0",
        "EventSubscriptionArn": "arn",
        "EventSource": "aws:sns",
        "Sns": {
            "SignatureVersion": "1",
            "Timestamp": "1970-01-01T00:00:00.000Z",
            "Signature": "EXAMPLE",
            "SigningCertUrl": "EXAMPLE",
            "MessageId": str(uuid.uuid4()),
            "Message": json.dumps(message.as_dict()),
            "MessageAttributes": {
                k: {"Value": str(v), "Type": "String"} for k, v in message.as_dict()['headers'].items()
            },
            "Type": "Notification",
            "UnsubscribeUrl": "EXAMPLE",
            "TopicArn": "arn",
            "Subject": "TestInvoke",
        },
    }

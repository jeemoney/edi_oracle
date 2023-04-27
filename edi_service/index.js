const { SQSClient, SendMessageCommand } = require("@aws-sdk/client-sqs");
const { S3Client, GetObjectCommand } = require("@aws-sdk/client-s3");
const sqs = new SQSClient();
const client = new S3Client({})
const { ediToOracle } = require("./edi_parser");

const producer = async (event) => {
  let message = "";
  for (const record of event.Records) {
    const bucketName = record.s3.bucket.name;
    const fileKey = record.s3.object.key;
    const eventTime = record.eventTime;
    console.log("Event: ", record.eventName);
    console.log("Bucket: ", bucketName);
    console.log("Key: ", fileKey);

    const params = {
      MessageGroupId: eventTime,
      QueueUrl: process.env.QUEUE_URL,
      MessageBody: 'New file uploaded',
      MessageAttributes: {
        BucketName: {
          StringValue: bucketName,
          DataType: "String",
        },
        FileKey: {
          StringValue: fileKey,
          DataType: "String",
        }

      },
    }
  
    try {
      await sqs.send(new SendMessageCommand(params));
      message = "Message accepted!";
    } catch (error) {
      console.log(error);
      message = error;
      statusCode = 500;
    }

    return {
      body: JSON.stringify({
        message,
      }),
    };
  };
};

const consumer = async (event) => {
  for (const record of event.Records) {
    const messageAttributes = record.messageAttributes;
    console.log(
      "Message Attribute: ",
      messageAttributes.BucketName.stringValue,
      messageAttributes.FileKey.stringValue
    );
    console.log("Message Body: ", record.body);

    const command = new GetObjectCommand({
      Bucket: messageAttributes.BucketName.stringValue,
      Key: messageAttributes.FileKey.stringValue,
    });

    try {
      const response = await client.send(command)
      const responseString = await response.Body.transformToString();
      const poDetails = await ediToOracle(responseString);
      console.log(poDetails);
    } catch (error) {
      console.log(error);
    }
  }
};

module.exports = {
  producer,
  consumer,
};

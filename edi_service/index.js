const { SQSClient, SendMessageCommand } = require("@aws-sdk/client-sqs");
const { S3Client, GetObjectCommand, CopyObjectCommand, DeleteObjectCommand } = require("@aws-sdk/client-s3");
const sqs = new SQSClient();
const s3Client = new S3Client({})
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
  let responses = []
  let processedPrefix = process.env.PROCESSED_BUCKET_PREFIX;
  for (const record of event.Records) {
    const messageAttributes = record.messageAttributes;
    console.log(
      "Message Attribute: ",
      messageAttributes.BucketName.stringValue,
      messageAttributes.FileKey.stringValue
    );
    console.log("Message Body: ", record.body);

    const getEDICommand = new GetObjectCommand({
      Bucket: messageAttributes.BucketName.stringValue,
      Key: messageAttributes.FileKey.stringValue,
    });

    const deleteObjectCommand = new DeleteObjectCommand({
      Bucket: messageAttributes.BucketName.stringValue,
      Key: messageAttributes.FileKey.stringValue,
    });
    
    // separate "incoming" subfolder prefix from file name
    // copy file to processed subfolder and delete from incoming
    const fileName = messageAttributes.FileKey.stringValue.split("/").pop();
    const copyObjectCommand = new CopyObjectCommand({
      Bucket: messageAttributes.BucketName.stringValue,
      CopySource: `${messageAttributes.BucketName.stringValue}/${messageAttributes.FileKey.stringValue}`,
      Key: `${processedPrefix}${fileName}`,
    });

    const getAccountSecretCommand = new GetObjectCommand({
      Bucket: messageAttributes.BucketName.stringValue,
      Key: process.env.ACCOUNT_PATH,
    });

    try {
      //Get EDI file from S3 and convert to string
      const ediData = await s3Client.send(getEDICommand)
      const ediString = await ediData.Body.transformToString();
      //Get account secret from S3 and convert to JSON
      //S3 is OK for dev/testing, but need to add support for Secrets Manager for production
      const accountData = await s3Client.send(getAccountSecretCommand);
      const accountString = await accountData.Body.transformToString();
      const account = JSON.parse(accountString);
      //Send EDI string and account to be parsed and sent to Oracle
      const txnResponse = await ediToOracle(ediString, account);
      //need to add logic to check if txnResponse was successful
      const copyResult = await s3Client.send(copyObjectCommand);
      const deleteResult = await s3Client.send(deleteObjectCommand);
      console.log(txnResponse);
      // need to format response to be more useful
      responses.push(txnResponse);
    } catch (error) {
      console.log(error);
      responses.push(error);
    }
  }
  return responses;
};

module.exports = {
  producer,
  consumer,
};

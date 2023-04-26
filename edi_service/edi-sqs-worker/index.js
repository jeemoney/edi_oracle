const { SQSClient, SendMessageCommand } = require("@aws-sdk/client-sqs");
const sqs = new SQSClient();

const producer = async (event) => {
  let file_key = event.object.key
  let message = "";

  try {
    await sqs.send(new SendMessageCommand({
      QueueUrl: process.env.QUEUE_URL,
      MessageBody: file_key,
      MessageAttributes: {
        AttributeName: {
          StringValue: "Attribute Value",
          DataType: "String",
        },
      },
    }));

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

const consumer = async (event) => {
  for (const record of event.Records) {
    const messageAttributes = record.messageAttributes;
    console.log(
      "Message Attribute: ",
      messageAttributes.AttributeName.stringValue
    );
    console.log("Message Body: ", record.body);
  }
};

module.exports = {
  producer,
  consumer,
};

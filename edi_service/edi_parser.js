const { X12Parser, X12QueryEngine } = require("node-x12");
const fs = require("fs");
const {
  Algodv2,
  AtomicTransactionComposer,
  default: algosdk,
} = require("algosdk");
const algoKitUtili = require("@algorandfoundation/algokit-utils");

const ediToJSON = (interchange) => {
  // get doc type for mapping
  const engine = new X12QueryEngine();
  const results = engine.query(interchange, "ST01");

  const { ediMap } = require("../edi_service/edi_mapper");
  const mapped = ediMap(results[0].value);

  let trans = [];

  interchange.functionalGroups.forEach((group) => {
    group.transactions.forEach((transaction) => {
      // There should only be one transaction
      trans.push(transaction.toObject(mapped));
    });
  });

  return trans[0];
};

const addEdiRecordToOracle = async (data) => {
  const appId = 94;

  let key, docType, ref, itemCode, itemQty, status;

  // temporary assigments
  key = data.DocType + data.PONumber;
  docType = parseInt(data.DocType);
  ref = data.PONumber;
  itemCode = data.ItemNumber;

  switch (data.DocType) {
    case "856":
      itemQty = parseInt(data.ShippedQty);
      status = 2;
      break;
    case "850":
      itemQty = parseInt(data.Quantity);
      status = 1;
      break;
    case "810":
      itemQty = parseInt(data.InvoiceQty);
      status = 0;
      break;

    default:
      itemQty = 0;
      status = -1;
      break;
  }

  // const sender = algosdk.mnemonicToSecretKey(
  //   "ignore elegant horror stamp bronze tooth wrestle category modify absent dish remember will stand include system antenna team aspect baby scissors object winter above educate"
  // );
  const client = new Algodv2(
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "http://localhost",
    "4001"
  );
  let sender = await algoKitUtili.getAccount(
    "brokertest1", //"PKS2W3G3MAEBFKODPGCI7I4UWGD3MOVR52MVJYRI2JT646ATT6BU6Q7FHU",
    client
  );

  let key32 = _bufferStrToFixed(key);
  console.log(`key_32: ${key32} with len ${key32.length}`);
  let ref32 = _bufferStrToFixed(ref);
  let itemCode32 = _bufferStrToFixed(itemCode);

  const appSpec = require("../contracts/artifacts/application.json");
  const contract = new algosdk.ABIContract(appSpec.contract);
  const suggestedParams = await client.getTransactionParams().do();

  const appArguments = {
    key: key32,
    doc_type: docType,
    ref: ref32,
    status: status,
    item_code: itemCode32,
    item_qty: itemQty,
  };

  const argumentValues = Object.values(appArguments);
  let appArgs = [];

  argumentValues.forEach((value) => {
    if (typeof value === "number") {
      appArgs.push(value);
    } else {
      appArgs.push(_stringToArray(value));
    }
  });

  const atc = new AtomicTransactionComposer();

  const txnSigner = algosdk.makeBasicAccountTransactionSigner(sender);

  const boxes = [{ appIndex: appId, name: _stringToArray(key32) }];

  atc.addMethodCall({
    appID: appId,
    method: contract.getMethodByName("add_record"),
    methodArgs: appArgs,
    sender: sender.addr,
    signer: txnSigner,
    boxes: boxes,
    suggestedParams: suggestedParams,
    appAccounts: [sender.addr],
  });
  const result = await atc.execute(client, 4);
  for (const mr of result.methodResults) {
    console.log(`${mr.txID}`);
  }

  result.methodResults[0].txID;
};

const _bufferStrToFixed = (string, length = 32) => {
  if (string.length == length) {
    return string.encode();
  }
  let buffer = "X".repeat(length - string.length - 1);
  return `${string}-${buffer}`;
};

function _stringToArray(bufferString) {
  let uint8Array = new TextEncoder("utf-8").encode(bufferString);
  return uint8Array;
}

const ediToOracle = async (data) => {
  const parser = new X12Parser(true);
  const interchange = parser.parse(data);
  let poJson = ediToJSON(interchange);
  await addEdiRecordToOracle(poJson);
};

// ** FOR LOCAL TESTING ONLY **
const ediParser = (fileName) => {
  const parser = new X12Parser(true);
  let interchange;
  // eslint-disable-next-line no-undef
  const sourcePath = __dirname + fileName;
  let edi = fs.readFileSync(sourcePath).toString();
  interchange = parser.parse(edi);
  return interchange;
};

module.exports = {
  ediParser,
  ediToJSON,
  addEdiRecordToOracle,
  ediToOracle,
};

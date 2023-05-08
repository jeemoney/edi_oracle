const { X12Parser, X12QueryEngine } = require("node-x12");
const fs = require("fs");
const {
  Algodv2,
  AtomicTransactionComposer,
  default: algosdk,
} = require("algosdk");
const algoKitUtili = require("@algorandfoundation/algokit-utils");

// helper functions
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

const _ediMap = (docType) => {
  const mappings = require("./edi_mapping.json");
  let map = {};
  const fieldMap = mappings[docType];
  fieldMap.fields.forEach((field) => {
    if (field.include) {
      map[field.code] = field.segment;
    }
  });

  return map;
};

// get edi segments via node-x12
const extractEDI = (data) => {
  const parser = new X12Parser(true);

  try {
    const interchange = parser.parse(data);
    return interchange;
  } catch (error) {
    throw `Failed to parse edi data: ${error.toString()}`;
  }
};

// get fields according to config and map edi transaction
const ediToJSON = (interchange) => {
  // get doc type for mapping
  const engine = new X12QueryEngine();
  const results = engine.query(interchange, "ST01");
  const fieldMap = _ediMap(results[0].value);

  let jsonTrans = [];

  interchange.functionalGroups.forEach((group) => {
    group.transactions.forEach((transaction) => {
      // There should only be one transaction
      jsonTrans.push(transaction.toObject(fieldMap));
    });
  });

  return jsonTrans[0];
};

// get smart contract parameters from jsonData
const getOracleParams = (jsonData) => {
  let params = {
    key: null,
    docType: null,
    ref: null,
    itemCode: null,
    itemQty: null,
    status: null,
  };

  // temporary assigments
  params.key = jsonData.docType + jsonData.purchNumber;
  params.docType = parseInt(jsonData.docType);
  params.ref = jsonData.purchNumber;
  params.itemCode = jsonData.itemNumber;

  switch (jsonData.docType) {
    case "856":
      params.itemQty = parseInt(jsonData.shippedQty);
      params.status = 2;
      break;
    case "850":
      params.itemQty = parseInt(jsonData.quantity);
      params.status = 1;
      break;
    case "810":
      itemQty = parseInt(jsonData.invoiceQuantity);
      params.status = 0;
      break;

    default:
      params.itemQty = 0;
      params.status = -1;
      break;
  }

  return params;
};

// create and send smart contract transaction call
const sendToOracle = async (params, accountSecret) => {
  // initialize client
  const token = process.env.ALGOD_TOKEN;
  const server = process.env.ALGOD_URL;
  const port = process.env.ALGOD_PORT;
  console.log(`server: ${server} port: ${port} token: ${token}`);
  const client = new Algodv2(token, server, port);

  // get application specifications for sc call
  const appSpec = require("./artifacts/application.json");
  const contract = new algosdk.ABIContract(appSpec.contract);
  const suggestedParams = await client.getTransactionParams();

  // prepare arguments for sc call
  const appId = parseInt(process.env.ORACLE_ID);
  const sender = algosdk.mnemonicToSecretKey(accountSecret.accountMnemonic);
  const key32 = _bufferStrToFixed(params.key);
  const ref32 = _bufferStrToFixed(params.ref);
  const itemCode32 = _bufferStrToFixed(params.itemCode);

  const appArguments = {
    key: key32,
    doc_type: params.docType,
    ref: ref32,
    status: params.status,
    item_code: itemCode32,
    item_qty: params.itemQty,
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

  return result.methodResults[0].txID;
};

// ETL sequence
const ediToOracle = async (data, accountSecret) => {
  // get JSEN data from file data
  const jsenData = extractEDI(data);

  // map JSEN data to config
  const jsonData = ediToJSON(jsenData);
  console.log(`poJson: ${JSON.stringify(jsonData)}`);
  // get params from data and send to oracle
  const params = getOracleParams(jsonData);
  const response = await sendToOracle(params, accountSecret);
  return response;
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
  getOracleParams,
  sendToOracle,
  ediToOracle,
};

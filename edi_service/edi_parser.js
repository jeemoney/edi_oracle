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

  // Map transaction sets to javascript objects
  let map = {};
  switch (results[0].value) {
    case "850":
      map = {
        docType: "ST01",
        // status: "GS01",
        poNumber: "BEG03",
        poDate: "BEG05",
        shipto_name: 'N102:N101["ST"]',
        shipto_address: 'N1-N301:N101["ST"]',
        shipto_city: 'N1-N401:N101["ST"]',
        shipto_state: 'N1-N402:N101["ST"]',
        shipto_zip: 'N1-N403:N101["ST"]',
        itemName: "PID05",
        quantity: "PO102",
        itemCode: "PO111",
        price: "PO104",
      };
      break;
    case "857":
      console.log(interchange);
      map = {
        docType: "ST01",
        // status: "GS01",
        poNumber: "BHT03",
        poDate: "BHT04",
        shipto_name: 'N102:N101["ST"]',
        itemName: "PID05",
        quantity: "IT102",
        itemCode: "IT107",
        price: "IT104",
      };
      break;

    default:
      break;
  }

  let transactions = [];

  interchange.functionalGroups.forEach((group) => {
    group.transactions.forEach((transaction) => {
      // There should only be one transaction
      transactions.push(transaction.toObject(map));
    });
  });

  return transactions[0];
};

const addEdiRecordToOracle = async (poDetails) => {
  const appId = 94;
  const key = poDetails.docType + poDetails.poNumber;
  const docType = parseInt(poDetails.docType);
  const ref = poDetails.poNumber;
  const itemCode = poDetails.itemCode;
  const itemQty = parseInt(poDetails.quantity);
  const status = 1;
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
      //const num = new Int32Array([value]).buffer;
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

// function getLocalKmdClient() {
//   const kmdToken = "a".repeat(64);
//   const kmdServer = "http://localhost";
//   const kmdPort = "4002";

//   const kmdClient = new algosdk.Kmd(kmdToken, kmdServer, kmdPort);
//   return kmdClient;
// }

// async function getLocalAccounts() {
//   const kmdClient = getLocalKmdClient();

//   const wallets = await kmdClient.listWallets();

//   let walletId;
//   // eslint-disable-next-line no-restricted-syntax
//   for (const wallet of wallets.wallets) {
//     if (wallet.name === "unencrypted-default-wallet") walletId = wallet.id;
//   }

//   if (walletId === undefined)
//     throw Error("No wallet named: unencrypted-default-wallet");

//   const handleResp = await kmdClient.initWalletHandle(walletId, "");
//   const handle = handleResp.wallet_handle_token;

//   const addresses = await kmdClient.listKeys(handle);
//   // eslint-disable-next-line camelcase
//   const acctPromises = [];

//   // eslint-disable-next-line no-restricted-syntax
//   for (const addr of addresses.addresses) {
//     acctPromises.push(kmdClient.exportKey(handle, "", addr));
//   }
//   const keys = await Promise.all(acctPromises);

//   // Don't need to wait for it
//   kmdClient.releaseWalletHandle(handle);

//   return keys.map((k) => {
//     const addr = algosdk.encodeAddress(k.private_key.slice(32));
//     const acct = { sk: k.private_key, addr };
//     const signer = algosdk.makeBasicAccountTransactionSigner(acct);

//     return {
//       addr: acct.addr,
//       privateKey: acct.sk,
//       signer,
//     };
//   });
// }

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

const { X12Parser } = require("node-x12");
const fs = require("fs");
const { Algodv2 } = require("algosdk");

const ediParser = (fileName) => {
  const parser = new X12Parser(true);
  let interchange;
  // eslint-disable-next-line no-undef
  const sourcePath = __dirname + fileName;
  let edi = fs.readFileSync(sourcePath).toString(); //.split("\n");
  interchange = parser.parse(edi);
  return interchange;
};

const ediToJSON = (interchange) => {
  // Map transaction sets to javascript objects
  const map = {
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

  let transactions = [];

  interchange.functionalGroups.forEach((group) => {
    group.transactions.forEach((transaction) => {
      // There should only be one transaction
      transactions.push(transaction.toObject(map));
    });
  });

  return transactions[0];

  // const engine = new X12QueryEngine();

  // .query for test
  // // const results = engine.query(interchange, "PID05");

  // results.forEach((result) => {
  //   // Do something with each result.
  //   console.log(result.value);
  //   // console.log(result.interchange);
  //   // console.log(result.functionalGroup);
  //   // console.log(result.transaction);
  //   // console.log(result.segment);
  //   // console.log(result.element);
  //   // console.log(result.value); //OR result.values
  // });
};

const sendToOracle = async () => {
  const client = new Algodv2(
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "http://localhost",
    "4001"
  );

  const acctInfo = await client
    .accountInformation(
      "M4KUGHBNYWUD7PAVBJBSURI3OMUL6PPOGJREJRLU7QBDSRLUZUMOVSKQLU"
    )
    .do();
  console.log(`Account balance: ${acctInfo.amount} microAlgos`);
};

module.exports = {
  ediParser,
  ediToJSON,
  sendToOracle,
};

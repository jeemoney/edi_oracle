const { X12Parser } = require("node-x12");
const fs = require("fs");

const ediParser = (fileName) => {
  if (fileName == null) {
    fileName = "/test_files/850_04222023.edi";
  }

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

  interchange.functionalGroups.forEach((group) => {
    group.transactions.forEach((transaction) => {
      // There should only be one transaction
      return transaction.toObject(map);
    });
  });

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
module.exports = {
  ediParser,
  ediToJSON,
};

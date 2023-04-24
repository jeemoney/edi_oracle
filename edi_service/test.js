"use strict";
const { ediParser, ediToJSON, sendToOracle } = require("./edi_parser");

const fileName = "/test_files/850_04222023.edi";
let edi = ediParser(fileName);
let poJson = ediToJSON(edi);
console.log(poJson);
sendToOracle();

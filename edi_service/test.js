"use strict";
const { ediParser, ediToJSON, addEdiRecordToOracle } = require("./edi_parser");
require("dotenv").config();

const fileName = "/test_files/850_04222023.edi";
let edi = ediParser(fileName);
let poJson = ediToJSON(edi);
console.log(poJson);
addEdiRecordToOracle(poJson);

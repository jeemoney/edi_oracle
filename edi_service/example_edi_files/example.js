"use strict";
const {
  ediParser,
  ediToJSON,
  getOracleParams,
  sendToOracle,
} = require("../edi_parser");
require("dotenv").config();

const fileName = "/example_edi_files/850_04302023.edi";
let edi = ediParser(fileName);
let poJson = ediToJSON(edi);
let params = getOracleParams(poJson);
sendToOracle(params, "");

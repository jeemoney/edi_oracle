"use-strict";

const ediMap = (docType) => {
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

module.exports = {
  ediMap,
};

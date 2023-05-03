"use-strict";

const ediMap = (docType) => {
  const mappings = require("./edi_mapping.json");
  let map = {};
  const fieldMap = mappings[docType];
  fieldMap.fields.forEach((field) => {
    if (field.include) {
      map[field.label.replace(/\s/g, "")] = field.segment;
    }
  });

  return map;
};

module.exports = {
  ediMap,
};

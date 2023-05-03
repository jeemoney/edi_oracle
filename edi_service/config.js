const fs = require("fs");

module.exports = async ({options, resolveVariable}) => {
    const stage = await resolveVariable("sls:stage");
    const configPath = await resolveVariable("param:configPath, './sls-config.json'");
    const configJSON = JSON.parse(fs.readFileSync(configPath).toString());
    const config = configJSON[stage];
    return config;
};
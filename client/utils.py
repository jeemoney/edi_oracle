import os
import base64
from json import JSONDecoder, JSONEncoder
import pyteal as pt
import algokit as ak
import algokit_utils as aku
from pathlib import Path

os.environ["ALGOD_SERVER"] = "http://localhost"
os.environ["ALGOD_PORT"] = "4001"
os.environ[
    "ALGOD_TOKEN"
] = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
os.environ["INDEXER_SERVER"] = "http://localhost"
os.environ["INDEXER_PORT"] = "8980"
os.environ[
    "INDEXER_TOKEN"
] = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def buffer_str_to_fixed(string: str, length: int = 32) -> bytes:
    if len(string) == length:
        return string.encode()
    buffer = "X" * (length - len(string) - 1)
    return "{0}-{1}".format(string, buffer).encode()


def create_app_client(app_id: int, creator: aku.Account) -> aku.ApplicationClient:
    return aku.ApplicationClient(
        aku.get_algod_client(),
        Path("../contracts/artifacts/application.json"),
        app_id=app_id,
        signer=creator,
    )


def create_account_map(account: aku.Account, role: str) -> dict[str, str]:
    return {
        "type": role,
        "address": account.address,
        "private_key": account.private_key,
    }


def create_accounts(
    brokers: list[str] = [],
    sellers: list[str] = [],
    buyers: list[str] = [],
) -> dict[str, dict[str, str]]:
    accounts_dict = {}
    for broker in brokers:
        account = aku.get_account(aku.get_algod_client(), broker)
        accounts_dict[broker] = create_account_map(account, "broker")

    for seller in sellers:
        account = aku.get_account(aku.get_algod_client(), seller)
        accounts_dict[seller] = create_account_map(account, "seller")

    for buyer in buyers:
        account = aku.get_account(aku.get_algod_client(), buyer)
        accounts_dict[buyer] = create_account_map(account, "buyer")

    json = JSONEncoder().encode(accounts_dict)
    with open("accounts.json", "w") as f:
        f.write(json)
    return accounts_dict

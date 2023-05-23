import argparse
import os
from json import JSONEncoder
from pathlib import Path

import algokit_utils as aku
from algosdk import atomic_transaction_composer as atc
from algosdk.abi import ABIType

from oracle.smart_contracts import edi_oracle
from oracle.smart_contracts.edi_oracle import EDIDocument, edi_oracle_app

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
    return f"{string}-{buffer}".encode()


def convert_buffered_to_str(buffered: list[int]) -> str:
    return bytearray(buffered).decode().split("-")[0]


def decode_edi_record(edi_record: tuple[int, str, int, str, int]) -> tuple:
    return (
        edi_record[0],
        convert_buffered_to_str(edi_record[1]),
        edi_record[2],
        convert_buffered_to_str(edi_record[3]),
        edi_record[4],
    )


def create_app_client(app_id: int, creator: aku.Account) -> aku.ApplicationClient:
    return aku.ApplicationClient(
        aku.get_algod_client(),
        Path("./artifacts/application.json"),
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
    brokers: list[str],
    sellers: list[str],
    buyers: list[str],
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


algod = aku.get_algod_client()
indexer = aku.get_indexer_client()
kmd = aku.get_kmd_client_from_algod_client(algod)

document_codec = ABIType.from_string(str(EDIDocument().type_spec()))


def create_edi_oracle(creator_name: str) -> tuple[int, str]:
    """Create a new EDI Oracle contract.
    This is a bare app call with the app ID set to 0."""
    creator_account = aku.get_account(algod, creator_name)
    app_client = create_app_client(0, creator_account)
    app_client.create(call_abi_method=False)

    app_address = app_client.app_address
    app_id = app_client.app_id
    return (app_id, app_address)


def setup_edi_oracle(oracle_client: aku.ApplicationClient, micro_algos: int) -> str:
    app_client = oracle_client
    app_address = app_client.app_address
    sp = app_client.algod_client.suggested_params()
    sp.flat_fee = True
    sp.fee = 2000
    min_balance = edi_oracle_app.state.min_balance.value
    print(min_balance)
    # if amount < min_balance:
    #     amount = min_balance
    params = aku.TransferParameters(
        from_account=app_client.signer,
        to_address=app_address,
        micro_algos=min_balance,
        suggested_params=sp,
    )
    payment = aku.transfer(algod, params)
    signer = app_client.signer
    result = app_client.call(
        edi_oracle.setup, payment_txn=atc.TransactionWithSigner(payment, signer)
    )
    return result.tx_id


def add_edi_record(
    oracle_client: aku.ApplicationClient,
    key: str,
    doc_type: int,
    ref: str,
    item_code: str,
    item_qty: int,
    status: int,
) -> str:
    key_32 = buffer_str_to_fixed(key)
    print(f"key_32: {key_32} with length {len(key_32)}")
    ref_32 = buffer_str_to_fixed(ref)
    print(f"ref_32: {ref_32} with length {len(ref_32)}")
    item_code_32 = buffer_str_to_fixed(item_code)
    print(f"item_code_32: {item_code_32} with length {len(item_code_32)}")

    app_client = oracle_client
    sp = app_client.algod_client.suggested_params()

    composer = atc.AtomicTransactionComposer()
    app_client.add_method_call(
        atc=composer,
        abi_method=edi_oracle.add_record,
        app_id=app_client.app_id,
        abi_args={
            "key": key_32,
            "doc_type": doc_type,
            "ref": ref_32,
            "status": status,
            "item_code": item_code_32,
            "item_qty": item_qty,
        },
        parameters=aku.CommonCallParameters(
            boxes=[(app_client.app_id, key_32)],
            suggested_params=sp,
        ),
    )
    response = app_client.execute_atc(composer)
    results = response.abi_results
    return bytearray(results[0].return_value).decode()


def get_edi_record(
    oracle_client: aku.ApplicationClient, key: str
) -> tuple[int, str, int, str, int]:
    app_client = oracle_client
    sp = app_client.algod_client.suggested_params()

    key_32 = buffer_str_to_fixed(key)
    composer = atc.AtomicTransactionComposer()
    app_client.add_method_call(
        atc=composer,
        abi_method=edi_oracle.get_record,
        app_id=app_client.app_id,
        abi_args={
            "key": key_32,
        },
        parameters=aku.CommonCallParameters(
            boxes=[(app_client.app_id, key_32)],
            suggested_params=sp,
        ),
    )
    result = app_client.execute_atc(composer)
    (
        arg1,
        arg2,
        arg3,
        arg4,
        arg5,
    ) = result.abi_results[0].return_value
    doc_type = int(arg1)
    ref = bytearray(arg2).decode("utf-8").split("-")[0]
    status = int(arg3)
    item_code = bytearray(arg4).decode("utf-8").split("-")[0]
    item_qty = int(arg5)

    return (
        doc_type,
        ref,
        status,
        item_code,
        item_qty,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", type=str, help="command to run")
    parser.add_argument(
        "-a", "--app_id", type=int, help="app id of the EDI Oracle", default=0
    )
    parser.add_argument("-s", "--sender", type=str, help="sender of the transaction")
    parser.add_argument(
        "--amount", type=int, help="amount of microalgos to send", default=0
    )
    parser.add_argument("-c", "--create", action="store_true", help="create the app")
    edi_record_group = parser.add_argument_group("edi_record")
    edi_record_group.add_argument("--key", type=str, help="key of the EDI record")
    edi_record_group.add_argument("--doc_type", type=int, help="type of the EDI record")
    edi_record_group.add_argument("--ref", type=str, help="ref of the EDI record")
    edi_record_group.add_argument(
        "--item_code", type=str, help="item code of the EDI record"
    )
    edi_record_group.add_argument(
        "--item_qty", type=int, help="item quantity of the EDI record"
    )
    edi_record_group.add_argument(
        "--status", type=int, help="status enum of the EDI record"
    )

    account_group = parser.add_argument_group("accounts")
    account_group.add_argument(
        "--brokers", type=str, help="comma-separated list of brokers"
    )
    account_group.add_argument(
        "--sellers", type=str, help="comma-separated list of sellers"
    )
    account_group.add_argument(
        "--buyers", type=str, help="comma-separated list of buyers"
    )
    # parser.add_argument("string", type=str, help="string to convert to base32")
    # parser.add_argument("string", type=str, help="string to convert to base32")
    args = parser.parse_args()
    # print(utf8_to_base32(args.string))
    if args.command == "build":
        response = edi_oracle.build_contract()
        print(response)
    elif args.command == "create":
        response = create_edi_oracle(args.sender)
        print(response)
    elif args.command == "setup":
        if args.app_id == 0 and args.create is True:
            sender = args.sender
            amount = args.amount
            print("compiling TEAL and building contract specification")
            build_result = edi_oracle.build_contract()
            print(build_result)
            print("creating EDI Oracle application")
            app_id, address = create_edi_oracle(sender)
            print(f"app_id: {app_id}")
            print(f"address: {address}")
            print("funding and setting up EDI Oracle application")
            sender = aku.get_account(algod, sender)
            oracle_client = create_app_client(app_id, sender)
            setup_result = setup_edi_oracle(oracle_client, amount)
            print(f"Setup Complete: {setup_result}")
        else:
            response = setup_edi_oracle(args.app_id, args.sender, args.amount)
            print(response)
    elif args.command == "create_accounts":
        brokers = args.brokers.split(",")
        sellers = args.sellers.split(",")
        buyers = args.buyers.split(",")
        response = create_accounts(buyers=buyers, sellers=sellers, brokers=brokers)
        print(response)
    elif args.command == "add_record":
        sender = aku.get_account(algod, args.sender)
        response = add_edi_record(
            oracle_client=create_app_client(args.app_id, sender),
            key=args.key,
            doc_type=args.doc_type,
            ref=args.ref,
            item_code=args.item_code,
            item_qty=args.item_qty,
            status=args.status,
        )
        print(response)
    elif args.command == "get_record":
        sender = args.sender
        key = args.key
        app_id = args.app_id
        doc_type, ref, status, item_code, item_qty = get_edi_record(
            app_id=app_id, sender=sender, key=key
        )
        print(
            "doc_type: {}, ref: {}, status: {}, item_code: {}, item_qty: {}".format(
                doc_type,
                ref,
                status,
                item_code,
                item_qty,
            )
        )


if __name__ == "__main__":
    main()

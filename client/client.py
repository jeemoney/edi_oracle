# take string passed in command line arg and convert to base32
import sys

sys.path.append("..")
import argparse
import utils
import pyteal as pt
import algosdk
from algosdk.abi import ABIType
from algosdk import atomic_transaction_composer as atc
import algokit as ak
import algokit_utils as aku
from contracts import edi_oracle
from contracts.edi_oracle import EDIDocument, edi_oracle_app


algod = aku.get_algod_client()
indexer = aku.get_indexer_client()
kmd = aku.get_kmd_client_from_algod_client(algod)

document_codec = ABIType.from_string(str(EDIDocument().type_spec()))


def create_edi_oracle(creator_name: str):
    """Create a new EDI Oracle contract.
    This is a bare app call with the app ID set to 0."""
    creator_account = aku.get_account(algod, creator_name)
    app_client = utils.create_app_client(0, creator_account)
    response = app_client.create(call_abi_method=False)

    app_address = app_client.app_address
    app_id = app_client.app_id
    return (app_id, app_address)


def setup_edi_oracle(app_id: int, sender: str, micro_algos: int):
    sender_account = aku.get_account(algod, sender)
    app_client = utils.create_app_client(app_id, sender_account)
    app_address = app_client.app_address
    sp = app_client.algod_client.suggested_params()
    sp.flat_fee = True
    sp.fee = 2000
    amount = micro_algos
    min_balance = edi_oracle_app.state.min_balance.value
    print(min_balance)
    # if amount < min_balance:
    #     amount = min_balance
    params = aku.TransferParameters(
        from_account=sender_account,
        to_address=app_address,
        micro_algos=min_balance,
        suggested_params=sp,
    )
    payment = aku.transfer(algod, params)
    signer = atc.AccountTransactionSigner(sender_account.private_key)
    result = app_client.call(
        edi_oracle.setup, payment_txn=atc.TransactionWithSigner(payment, signer)
    )
    return result.tx_id


def add_edi_record(
    app_id: int,
    sender: str,
    key: str,
    doc_type: int,
    ref: str,
    item_code: str,
    item_qty: int,
    status: int,
):
    key_32 = utils.buffer_str_to_fixed(key)
    print("key_32: {0} with length {1}".format(key_32, len(key_32)))
    ref_32 = utils.buffer_str_to_fixed(ref)
    print("ref_32: {0} with length {1}".format(ref_32, len(ref_32)))
    item_code_32 = utils.buffer_str_to_fixed(item_code)
    print("item_code_32: {0} with length {1}".format(item_code_32, len(item_code_32)))
    sender_account = aku.get_account(algod, sender)
    app_client = utils.create_app_client(app_id, sender_account)
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
    result = app_client.execute_atc(composer)

    return result.tx_ids


def get_edi_record(app_id: int, sender: str, key: str):
    sender_account = aku.get_account(algod, sender)
    app_client = utils.create_app_client(app_id, sender_account)
    sp = app_client.algod_client.suggested_params()

    key_32 = utils.buffer_str_to_fixed(key)
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
    # print(utils.utf8_to_base32(args.string))
    if args.command == "create":
        response = create_edi_oracle(args.sender)
        print(response)
    elif args.command == "setup":
        if args.app_id == 0 and args.create == True:
            sender = args.sender
            amount = args.amount
            print("compiling TEAL and building contract specification")
            build_result = edi_oracle.build_contract()
            print(build_result)
            print("creating EDI Oracle application")
            app_id, address = create_edi_oracle(sender)
            print("app_id: {0}".format(app_id))
            print("address: {0}".format(address))
            print("funding and setting up EDI Oracle application")
            setup_result = setup_edi_oracle(app_id, sender, amount)
            print("Setup Complete: {}".format(setup_result))
        else:
            response = setup_edi_oracle(args.app_id, args.sender, args.amount)
            print(response)
    elif args.command == "create_accounts":
        brokers = args.brokers.split(",")
        sellers = args.sellers.split(",")
        buyers = args.buyers.split(",")
        response = utils.create_accounts(
            buyers=buyers, sellers=sellers, brokers=brokers
        )
        print(response)
    elif args.command == "add_record":
        response = add_edi_record(
            app_id=args.app_id,
            sender=args.sender,
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
            "doc_type: {0}, ref: {1}, status: {2}, item_code: {3}, item_qty: {4}".format(
                doc_type,
                ref,
                status,
                item_code,
                item_qty,
            )
        )


if __name__ == "__main__":
    main()

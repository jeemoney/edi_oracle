import json
from typing import Final, Literal as L
from pyteal import (
    Itob,
    Log,
    abi,
    Assert,
    Bytes,
    Concat,
    Expr,
    Global,
    If,
    Int,
    Len,
    Seq,
    ScratchVar,
    Subroutine,
    TealType,
    While,
)
import beaker
from beaker.consts import BOX_FLAT_MIN_BALANCE, BOX_BYTE_MIN_BALANCE
from beaker.lib.storage import BoxList, BoxMapping


CONTRACT_VERSION = "0.0.3"


class EDIDocument(abi.NamedTuple):
    doc_type: abi.Field[abi.Uint16]
    ref: abi.Field[abi.StaticBytes[L[32]]]
    status: abi.Field[abi.Uint8]
    item_code: abi.Field[abi.StaticBytes[L[32]]]
    item_qty: abi.Field[abi.Uint64]


class EDIOracleState:
    setup_complete: Final[beaker.GlobalStateValue] = beaker.GlobalStateValue(
        stack_type=TealType.uint64, default=Int(0)
    )

    def __init__(
        self,
        *,
        max_documents: int,
        record_type: type[abi.BaseType],
    ):
        self.max_documents = max_documents

        self.edi_records = BoxMapping(
            abi.StaticBytes[L[32]],
            record_type,
        )
        self.min_balance = Int(
            (
                BOX_FLAT_MIN_BALANCE
                + (abi.size_of(record_type) * BOX_BYTE_MIN_BALANCE)
                + (32 * BOX_BYTE_MIN_BALANCE)
            )
            * max_documents
        )


edi_oracle_app = beaker.Application(
    "EDIOracle_v{}".format(CONTRACT_VERSION),
    state=EDIOracleState(max_documents=100, record_type=EDIDocument),
)


@edi_oracle_app.external(authorize=beaker.Authorize.only_creator())
def setup(payment_txn: abi.PaymentTransaction, *, output: abi.String) -> Expr:
    return Seq(
        Assert(
            payment_txn.get().receiver() == Global.current_application_address(),
            comment="Payment must be sent to this contract",
        ),
        Assert(
            payment_txn.get().amount() >= edi_oracle_app.state.min_balance,
            comment="Payment must be enough to cover box storage minimum balance",
        ),
        edi_oracle_app.state.setup_complete.set(Int(1)),
        output.set("Setup complete"),
    )


# It is best practice to store static values in boxes to avoid high minimum balance requirements
# This function converts a string to a fixed length byte array by appending a - followed by 0s
@Subroutine(TealType.bytes)
def string_to_static_len(
    string: abi.String,
    length: abi.Uint64,
) -> Expr:
    return Seq(
        (new_string := ScratchVar(type=TealType.bytes)).store(string.get()),
        If(Len(new_string.load()) < length.get()).Then(
            new_string.store(Concat(new_string.load(), Bytes("-")))
        ),
        While(Len(new_string.load()) < length.get()).Do(
            new_string.store(
                Concat(
                    string.get(),
                    Bytes("0"),
                )
            )
        ),
        new_string.load(),
    )


@edi_oracle_app.external(authorize=beaker.Authorize.only_creator())
def add_record(
    key: abi.StaticBytes[L[32]],
    doc_type: abi.Uint16,
    ref: abi.StaticBytes[L[32]],
    status: abi.Uint8,
    item_code: abi.StaticBytes[L[32]],
    item_qty: abi.Uint64,
) -> Expr:
    return Seq(
        Assert(
            edi_oracle_app.state.setup_complete.get() == Int(1),
            comment="Setup must be complete",
        ),
        Assert(ref.length() <= Int(32), comment="Ref must be <= 32 bytes"),
        Assert(item_code.length() <= Int(32), comment="Item code must be <= 32 bytes"),
        Assert(key.length() <= Int(32), comment="Key must be < 32 bytes"),
        (edi_record := EDIDocument()).set(
            doc_type,
            ref,
            status,
            item_code,
            item_qty,
        ),
        edi_oracle_app.state.edi_records[key.get()].set(edi_record),
    )


@edi_oracle_app.external(read_only=True)
def get_record(key: abi.StaticBytes[L[32]], *, output: EDIDocument) -> Expr:
    return Seq(
        Assert(
            edi_oracle_app.state.setup_complete.get() == Int(1),
            comment="Setup must be complete",
        ),
        edi_oracle_app.state.edi_records[key.get()].store_into(output),
    )


def build_contract():
    app = edi_oracle_app.build()
    app.export("./artifacts")
    app.export("../edi_service/artifacts")
    return "Application: {} built".format(app.contract.name)


if __name__ == "__main__":
    build_contract()

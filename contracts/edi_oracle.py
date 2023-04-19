import json
from typing import Final, Literal as L
from pyteal import *
import pyteal as pt
import beaker
from beaker.consts import BOX_FLAT_MIN_BALANCE, BOX_BYTE_MIN_BALANCE
from beaker.lib.storage import BoxList, BoxMapping


class EDIDocument(abi.NamedTuple):
    doc_type: abi.Field[abi.Uint8]
    ref: abi.Field[abi.StaticBytes[L[32]]]
    status: abi.Field[abi.Uint8]
    item_code: abi.Field[abi.StaticBytes[L[32]]]
    item_qty: abi.Field[abi.Uint64]


class EDIOracleState:
    setup_complete: Final[beaker.GlobalStateValue] = beaker.GlobalStateValue(
        stack_type=TealType.uint64, default=Int(0)
    )

    def __init__(self, *, max_documents: int, record_type: type[abi.BaseType]):
        self.max_documents = max_documents
        self.edi_records = BoxMapping(
            abi.String,
            record_type,
        )
        self.min_balance = Int(
            (BOX_FLAT_MIN_BALANCE + (abi.size_of(record_type) * BOX_BYTE_MIN_BALANCE))
            * max_documents
        )


edi_oracle_app = beaker.Application(
    "EDIOracle", state=EDIOracleState(max_documents=10, record_type=EDIDocument)
)


@edi_oracle_app.external(authorize=beaker.Authorize.only_creator())
def setup(payment_txn: abi.PaymentTransaction, *, output: abi.String):
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


@edi_oracle_app.external(authorize=beaker.Authorize.only_creator())
def add_record(
    doc_type: abi.Uint8,
    ref: abi.StaticBytes[L[32]],
    status: abi.Uint8,
    item_code: abi.StaticBytes[L[32]],
    item_qty: abi.Uint64,
):
    return Seq(
        Assert(
            edi_oracle_app.state.setup_complete.get() == Int(1),
            comment="Setup must be complete",
        ),
        (doc_key := ScratchVar(type=TealType.bytes)).store(
            Concat(ref.get(), Itob(doc_type.get()))
        ),
        (edi_record := EDIDocument()).set(
            doc_type,
            ref,
            status,
            item_code,
            item_qty,
        ),
        edi_oracle_app.state.edi_records[doc_key.load()].set(edi_record),
    )


@edi_oracle_app.external(read_only=True)
def get_record(
    ref: abi.StaticBytes[L[32]], doc_type: abi.Uint8, *, output: EDIDocument
):
    return Seq(
        Assert(
            edi_oracle_app.state.setup_complete.get() == Int(1),
            comment="Setup must be complete",
        ),
        (doc_key := ScratchVar(type=TealType.bytes)).store(
            Concat(ref.get(), Itob(doc_type.get()))
        ),
        edi_oracle_app.state.edi_records[doc_key.load()].store_into(output),
    )


if __name__ == "__main__":
    app = edi_oracle_app.build()
    app.export("./artifacts")

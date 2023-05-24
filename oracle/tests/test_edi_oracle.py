import pytest
from algokit_utils import (
    ApplicationClient,
    ApplicationSpecification,
    LogicError,
    get_account,
    get_localnet_default_account,
)
from algosdk.v2client.algod import AlgodClient

from oracle.smart_contracts import edi_oracle
from oracle.smart_contracts.oracle_cli import (
    add_edi_record,
    buffer_str_to_fixed,
    get_edi_record,
    setup_edi_oracle,
)


@pytest.fixture(scope="session")
def oracle_app_spec(algod_client: AlgodClient) -> ApplicationSpecification:
    return edi_oracle.edi_oracle_app.build(algod_client)


@pytest.fixture(scope="session")
def oracle_client(
    algod_client: AlgodClient, oracle_app_spec: ApplicationSpecification
) -> ApplicationClient:
    sender = get_localnet_default_account(algod_client)
    client = ApplicationClient(
        algod_client,
        app_spec=oracle_app_spec,
        signer=sender,
        template_values={"UPDATABLE": 1, "DELETABLE": 1},
    )
    client.create()
    setup_edi_oracle(client, 0)
    return client


def fake_edi_record() -> tuple:
    return (850, "abc123", 1, "123", 1)


def test_add_record(oracle_client: ApplicationClient) -> None:
    edi_values = fake_edi_record()
    results = add_edi_record(
        oracle_client=oracle_client,
        key=str(edi_values[0]) + edi_values[1],
        doc_type=edi_values[0],
        ref=edi_values[1],
        status=edi_values[2],
        item_code=edi_values[3],
        item_qty=edi_values[4],
    )
    # Oracle returns the key as a fixed length bytearray
    # and the client converts it to a string
    # Compare the combined and buffered doc_type
    # and ref values as a string to the returned key
    assert results == buffer_str_to_fixed(str(edi_values[0]) + edi_values[1]).decode()


def test_add_record_fails_when_not_creator(
    algod_client: AlgodClient,
    oracle_client: ApplicationClient,
    oracle_app_spec: ApplicationSpecification,
) -> None:
    new_account = get_account(client=algod_client, name="Test_Account")
    client = ApplicationClient(
        algod_client,
        app_id=oracle_client.app_id,
        app_spec=oracle_app_spec,
        signer=new_account,
        template_values={"UPDATABLE": 1, "DELETABLE": 1},
    )

    edi_values = fake_edi_record()
    with pytest.raises(LogicError):
        add_edi_record(
            oracle_client=client,
            key=str(edi_values[0]) + edi_values[1],
            doc_type=edi_values[0],
            ref=edi_values[1],
            status=edi_values[2],
            item_code=edi_values[3],
            item_qty=edi_values[4],
        )


def test_get_edi_record(oracle_client: ApplicationClient) -> None:
    edi_values = fake_edi_record()

    results = get_edi_record(
        oracle_client=oracle_client, key=str(edi_values[0]) + edi_values[1]
    )
    assert results == edi_values


def test_get_record_logic_error_when_key_not_found(
    oracle_client: ApplicationClient,
) -> None:
    fake_edi_record()
    with pytest.raises(LogicError):
        get_edi_record(oracle_client=oracle_client, key="bad_key")

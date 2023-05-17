import pytest
from algokit_utils import (
    ApplicationClient,
    ApplicationSpecification,
    get_localnet_default_account,
)
from algosdk.v2client.algod import AlgodClient

from oracle.smart_contracts import edi_oracle
from oracle.smart_contracts.oracle_cli import add_edi_record


@pytest.fixture(scope="session")
def oracle_app_spec(algod_client: AlgodClient) -> ApplicationSpecification:
    return edi_oracle.edi_oracle_app.build(algod_client)


@pytest.fixture(scope="session")
def oracle_client(
    algod_client: AlgodClient, oracle_app_spec: ApplicationSpecification
) -> ApplicationClient:
    client = ApplicationClient(
        algod_client,
        app_spec=oracle_app_spec,
        signer=get_localnet_default_account(algod_client),
        template_values={"UPDATABLE": 1, "DELETABLE": 1},
    )
    client.create()
    return client


def test_add_record(oracle_client: ApplicationClient) -> None:
    results = add_edi_record(
        app_id=oracle_client.app_id,
        oracle_client=oracle_client,
        sender="DEPLOYER",
        key="850abc123",
        doc_type=850,
        ref="abc123",
        item_code="123",
        item_qty=1,
        status=1,
    )

    assert len(results) == 1

import pytest
from algokit_utils import (
    ApplicationClient,
    ApplicationSpecification,
    get_localnet_default_account,
)
from algosdk.v2client.algod import AlgodClient

from smart_contracts import edi_oracle


@pytest.fixture(scope="session")
def oracle_app_spec(algod_client: AlgodClient) -> ApplicationSpecification:
    return edi_oracle.app.build(algod_client)


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


def test_says_hello(oracle_client: ApplicationClient) -> None:
    result = oracle_client.call(edi_oracle.hello, name="World")

    assert result.return_value == "Hello, World"

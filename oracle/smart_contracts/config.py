import logging

from algokit_utils import (
    Account,
    ApplicationClient,
    ApplicationSpecification,
    OnSchemaBreak,
    OnUpdate,
    OperationPerformed,
    TransferParameters,
    is_localnet,
    transfer,
)
from algosdk.constants import MIN_TXN_FEE
from algosdk.transaction import PaymentTxn
from algosdk.util import algos_to_microalgos
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient

from oracle.smart_contracts import edi_oracle, helloworld

logger = logging.getLogger(__name__)

# define contracts to build and/or deploy
contracts = [helloworld.app, edi_oracle.edi_oracle_app]


# define deployment behaviour based on supplied app spec
def deploy(
    algod_client: AlgodClient,
    indexer_client: IndexerClient,
    app_spec: ApplicationSpecification,
    deployer: Account,
) -> None:
    is_local = is_localnet(algod_client)
    print(f"Deploying {app_spec.contract.name}...")
    match app_spec.contract.name:
        case "EDIOracle_v0.0.3":
            edi_oracle.build_contract()
            app_client = ApplicationClient(
                algod_client,
                app_spec,
                creator=deployer,
                indexer_client=indexer_client,
            )
            deploy_response = app_client.deploy(
                on_schema_break=(
                    OnSchemaBreak.ReplaceApp if is_local else OnSchemaBreak.Fail
                ),
                on_update=OnUpdate.UpdateApp if is_local else OnUpdate.Fail,
                allow_delete=is_local,
                allow_update=is_local,
            )

            # if only just created, fund smart contract account
            if deploy_response.action_taken in [
                OperationPerformed.Create,
                OperationPerformed.Replace,
            ]:
                min_balance = edi_oracle.edi_oracle_app.state.get_min_balance()
                params = TransferParameters(
                    from_account=deployer,
                    to_address=app_client.app_address,
                    micro_algos=min_balance,
                )
                logger.info(
                    f"New app created, funding with " f"{params.micro_algos}µ algos"
                )
                suggested_params = (
                    params.suggested_params or algod_client.suggested_params()
                )
                transaction = PaymentTxn(
                    sender=deployer,
                    receiver=params.to_address,
                    amt=params.micro_algos,
                    note=params.note.encode("utf-8")
                    if isinstance(params.note, str)
                    else params.note,
                    sp=suggested_params,
                )
                if params.fee_micro_algos:
                    transaction.fee = params.fee_micro_algos

                if not suggested_params.flat_fee:
                    if transaction.fee > params.max_fee_micro_algos:
                        raise Exception(
                            f"Cancelled transaction due to high network congestion fees. "
                            f"Algorand suggested fees would cause this transaction to cost {transaction.fee} µALGOs. "
                            f"Cap for this transaction is {params.max_fee_micro_algos} µALGOs."
                        )
                    if transaction.fee > MIN_TXN_FEE:
                        logger.warning(
                            f"Algorand network congestion fees are in effect. "
                            f"This transaction will incur a fee of {transaction.fee} µALGOs."
                        )
                signed_txn = transaction.sign(params.from_account.private_key)

                response = app_client.call("setup", payment_txn=signed_txn)
                logger.info(
                    f"Called hello on {app_spec.contract.name} ({app_client.app_id}) "
                    f"received: {response.return_value}"
                )
        case "HelloWorldApp":
            app_client = ApplicationClient(
                algod_client,
                app_spec,
                creator=deployer,
                indexer_client=indexer_client,
            )
            deploy_response = app_client.deploy(
                on_schema_break=(
                    OnSchemaBreak.ReplaceApp if is_local else OnSchemaBreak.Fail
                ),
                on_update=OnUpdate.UpdateApp if is_local else OnUpdate.Fail,
                allow_delete=is_local,
                allow_update=is_local,
            )

            # if only just created, fund smart contract account
            if deploy_response.action_taken in [
                OperationPerformed.Create,
                OperationPerformed.Replace,
            ]:
                params = TransferParameters(
                    from_account=deployer,
                    to_address=app_client.app_address,
                    micro_algos=algos_to_microalgos(1),
                )
                logger.info(
                    f"New app created, funding with " f"{params.micro_algos}µ algos"
                )
                transfer(algod_client, params)

            name = "world"
            response = app_client.call("hello", name=name)
            logger.info(
                f"Called hello on {app_spec.contract.name} ({app_client.app_id}) "
                f"with name={name}, received: {response.return_value}"
            )
        case _:
            raise Exception(
                f"Attempt to deploy unknown contract {app_spec.contract.name}"
            )

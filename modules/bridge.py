from eth_abi import abi
from client.client import Client
from utils.logger import logger


class Bridge:
    def __init__(self, client: Client, from_network: dict, to_network: dict, amount: int, pool_abi: list):
        self.client = client
        self.amount = amount
        self.pool_abi = pool_abi
        self.from_network = from_network
        self.to_network = to_network
        self.pool_contract = None

    @classmethod
    async def create(cls, client, from_network, to_network, amount, pool_abi):
        self = cls(client, from_network, to_network, amount, pool_abi)
        self.pool_contract = await self.client.get_contract(contract_address=client.pool_address, abi=pool_abi)
        return self

    async def get_bridge_fee(self, send_params: list):
        bridge_fee = await self.pool_contract.functions.quoteSend(send_params, False).call()
        return bridge_fee

    async def wait_orbiter_status(self, tx_hash: str, timeout: int = 120, interval: int = 10) -> bool:

        pass

    async def execute_bridge(self):

        try:
            send_params = [
                self.to_network['endpoint_id'],
                abi.encode(["address"], [self.client.address]),
                self.amount,
                int(self.amount * 0.995),
                b'0x',
                b'0x',
                b'0x1'
            ]
            print(send_params)

            bridge_fee = await self.get_bridge_fee(send_params)
            print(bridge_fee)
            fee = await self.client.from_wei_main(bridge_fee[0])
            print(fee)
            exit(1)
            value = int(self.amount + bridge_fee[0])
            tx = await self.pool_contract.functions.send(
                send_params,
                bridge_fee,
                self.client.address
            ).build_transaction(await self.client.prepare_tx(value))
            70548425772164
            27900922378997
            tx_hash = await self.client.sign_and_send_tx(tx)
            await self.client.wait_tx(tx_hash, self.client.explorer_url)
            return
        except Exception as e:
            logger.error(f"{e}")

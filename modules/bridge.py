from eth_abi import abi
from client.client import Client
from utils.logger import logger
from utils.balance_checker import check_balance


class Bridge:
    def __init__(self, client: Client, from_network: dict, to_network: dict, settings: dict, pool_abi: list):
        self.client = client
        self.pool_abi = pool_abi
        self.from_network = from_network
        self.to_network = to_network
        self.settings = settings
        self.pool_contract = None

    @classmethod
    async def create(cls, client, from_network, to_network, settings, pool_abi):
        """
        Создает и инициализирует экземпляр Bridge.
        
        Args:
            client: Экземпляр клиента Web3
            from_network: Словарь с данными исходной сети
            to_network: Словарь с данными целевой сети
            settings: Настройки бриджа
            pool_abi: ABI смарт-контракта пула
            
        Returns:
            Bridge: Инициализированный экземпляр Bridge
        """
        self = cls(client, from_network, to_network, settings, pool_abi)
        self.pool_contract = await self.client.get_contract(contract_address=client.pool_address, abi=pool_abi)
        return self

    async def get_fee_n_quote(self, send_params: list):
        """
        Получает комиссию и котировку для бриджа.
        
        Args:
            send_params: Параметры для отправки токенов
            
        Returns:
            tuple: (bridge_fee, quote_oft) - комиссия за бридж и котировка OFT
        """
        bridge_fee = await self.pool_contract.functions.quoteSend(send_params, False).call()
        quote_oft = await self.pool_contract.functions.quoteOFT(send_params).call()
        return bridge_fee, quote_oft

    async def execute_bridge(self):
        """
        Выполняет бридж токенов через Stargate в режиме fast.
        
        Включает следующие шаги:
        1. Расчет комиссии и котировки
        2. Проверка баланса
        3. Выполнение необходимого approve (для ERC-20 токенов)
        4. Отправка транзакции бриджа
        5. Ожидание подтверждения транзакции
        
        Returns:
            bool: True, если бридж успешно выполнен
        """
        try:
            send_params = [
                self.to_network['endpoint_id'],
                abi.encode(["address"], [self.client.address]),
                self.client.amount,
                int(self.client.amount * 0.995),
                b'',
                b'',
                b''
            ]

            bridge_fee, quote_oft = await self.get_fee_n_quote(send_params)

            await check_balance(self.client, self.from_network, self.settings, bridge_fee[0])

            # Для ETH нужно отправить сумму токена + комиссию как value
            if self.settings["token"] != "ETH":
                value = int(bridge_fee[0])
            else:
                value = int(self.client.amount + bridge_fee[0])

            send_params = [
                self.to_network['endpoint_id'],
                abi.encode(["address"], [self.client.address]),
                self.client.amount,
                quote_oft[2][1],
                b'',
                b'',
                b''
            ]

            tx = await self.pool_contract.functions.send(
                send_params,
                bridge_fee,
                self.client.address
            ).build_transaction(await self.client.prepare_tx(value))

            amount_approve = 2 ** 256 - 1

            if self.settings["token"] == "USDC":
                allowance = await self.client.get_allowance(self.from_network["usdc_address"], self.client.address,
                                                            self.from_network["usdc_pool_address"])
                if allowance < amount_approve:
                    await self.client.approve_usdc(self.from_network["usdc_address"],
                                                   self.from_network["usdc_pool_address"],
                                                   amount_approve, True)

            tx_hash = await self.client.sign_and_send_tx(tx)
            result = await self.client.wait_tx(tx_hash, self.client.explorer_url)
            if result:
                logger.info(f"💵 Бридж совершен, ожидайте поступления средств в сети назначения...")
                return True
            return False
        except Exception as e:
            logger.error(f"{e}")
            return False

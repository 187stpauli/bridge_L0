from web3 import AsyncWeb3, AsyncHTTPProvider
from utils.logger import logger
import asyncio
import time


class BridgeTracker:
    """
    Класс для отслеживания статуса бриджа в сети назначения.
    Позволяет проверить, были ли получены токены в сети назначения.
    """
    def __init__(self, destination_rpc: str, destination_explorer: str, wallet_address: str, token_address: str = None, proxy: str = None):
        """
        Инициализирует трекер бриджа.
        
        Args:
            destination_rpc: URL RPC-провайдера сети назначения
            destination_explorer: URL блок-эксплорера сети назначения
            wallet_address: Адрес кошелька получателя
            token_address: Адрес токена в сети назначения (для ERC-20)
            proxy: Прокси для подключения (опционально)
        """
        request_kwargs = {"proxy": f"http://{proxy}"} if proxy else {}
        self.w3 = AsyncWeb3(AsyncHTTPProvider(destination_rpc, request_kwargs=request_kwargs))
        self.explorer_url = destination_explorer
        self.wallet_address = self.w3.to_checksum_address(wallet_address)
        self.token_address = token_address
        self.is_native = token_address is None
    
    async def check_balance_change(self, timeout: int = 300) -> bool:
        """
        Отслеживает изменение баланса в сети назначения.
        
        Args:
            timeout: Максимальное время ожидания в секундах
            
        Returns:
            bool: True, если обнаружено изменение баланса, иначе False
        """
        logger.info(f"🔍 Отслеживаем получение средств в сети назначения...")
        
        if self.is_native:
            # Для нативного токена (ETH)
            initial_balance = await self.w3.eth.get_balance(self.wallet_address)
        else:
            # Для ERC-20 токенов
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ]
            token_contract = self.w3.eth.contract(address=self.w3.to_checksum_address(self.token_address), abi=erc20_abi)
            initial_balance = await token_contract.functions.balanceOf(self.wallet_address).call()
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            await asyncio.sleep(10)  # Проверяем каждые 10 секунд
            
            if self.is_native:
                current_balance = await self.w3.eth.get_balance(self.wallet_address)
            else:
                token_contract = self.w3.eth.contract(
                    address=self.w3.to_checksum_address(self.token_address), 
                    abi=erc20_abi
                )
                current_balance = await token_contract.functions.balanceOf(self.wallet_address).call()
            
            if current_balance > initial_balance:
                logger.info(f"✅ Средства успешно получены в сети назначения!")
                return True
                
            logger.info(f"⏳ Ожидаем поступления средств... Прошло {int(time.time() - start_time)} сек.")
        
        logger.warning(f"⚠️ Превышено время ожидания. Средства могут поступить позже, проверьте баланс вручную.")
        return False 
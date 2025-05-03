from config.configvalidator import ConfigValidator
from client.client import Client
from modules.bridge import Bridge
from utils.logger import logger
import asyncio
import json

with open("abi/native_pool_abi.json", "r", encoding="utf-8") as f:
    NATIVE_POOL = json.load(f)

with open("abi/usdc_pool_abi.json", "r", encoding="utf-8") as f:
    USDC_POOL = json.load(f)


async def main():
    try:
        logger.info("🚀 Запуск скрипта...\n")
        # Загрузка параметров
        logger.info("⚙️ Загрузка и валидация параметров...\n")
        validator = ConfigValidator("config/settings.json")
        settings = await validator.validate_config()

        with open("constants/networks_data.json", "r", encoding="utf-8") as file:
            networks_data = json.load(file)

        from_network = networks_data[settings["from_network"]]
        to_network = networks_data[settings["to_network"]]

        pool_address = None
        pool_abi = None
        if settings["token"] == "USDC":
            pool_abi = USDC_POOL
            pool_address = from_network["usdc_pool_address"]
        elif settings["token"] == "ETH":
            pool_abi = NATIVE_POOL
            pool_address = from_network["native_pool_address"]

        # Инициализация клиента
        client = Client(
            proxy=settings["proxy"],
            rpc_url=from_network["rpc_url"],
            chain_id=from_network["chain_id"],
            private_key=settings["private_key"],
            pool_address=pool_address,
            amount=settings["amount"],
            token=settings["token"],
            explorer_url=from_network["explorer_url"]
        )

        real_amount = 0
        if settings["token"] == "USDC":
            real_amount = await client.to_wei_main(client.amount, from_network['usdc_address'])
        elif settings["token"] == "ETH":
            real_amount = await client.to_wei_main(client.amount)
        await client.set_amount(real_amount)

        # Запуск бриджа
        logger.info("⚙️ Собираем и подписываем транзакцию...\n")
        bridge = await Bridge.create(client, from_network, to_network, settings, pool_abi)
        await bridge.execute_bridge()

    except Exception as e:
        logger.error(f"Произошла ошибка в основном пути: {e}")


if __name__ == "__main__":
    asyncio.run(main())

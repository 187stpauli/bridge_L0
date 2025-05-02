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
            explorer_url=from_network["explorer_url"]
        )

        amount_in = 0
        if settings["token"] == "USDC":
            amount_in = await client.to_wei_main(settings["amount"], from_network['usdc_address'])
        elif settings["token"] == "ETH":
            amount_in = await client.to_wei_main(settings["amount"])

        # Проверка баланса
        native_balance = await client.get_native_balance()
        gas = await client.get_tx_fee()

        if settings["token"] == "USDC":
            balance = await client.get_erc20_balance(from_network["usdc_address"])
            if amount_in > balance:
                logger.error(f"Недостаточно баланса {settings['token']}! Требуется: "
                             f"{await client.from_wei_main(amount_in):.8f} "
                             f"фактический баланс: "
                             f"{await client.from_wei_main(balance, from_network['usdc_address']):.8f}\n")
                exit(1)
            if gas > native_balance:
                logger.error(f"Недостаточно баланса для оплаты газа! Требуется: "
                             f"{await client.from_wei_main(gas):.8f} "
                             f"фактический баланс: {await client.from_wei_main(native_balance):.8f}\n")
                exit(1)
        elif settings["token"] == "ETH":
            total_cost = amount_in + gas
            if total_cost > native_balance:
                logger.error(f"Недостаточно баланса! Требуется: {await client.from_wei_main(total_cost):.8f}"
                             f" фактический баланс: {await client.from_wei_main(native_balance):.8f}\n")
                exit(1)

        # Запуск бриджа
        logger.info("⚙️ Собираем и подписываем транзакцию...\n")
        bridge = await Bridge.create(client, from_network, to_network, amount_in, pool_abi)
        await bridge.execute_bridge()

    except Exception as e:
        logger.error(f"Произошла ошибка в основном пути: {e}")


if __name__ == "__main__":
    asyncio.run(main())

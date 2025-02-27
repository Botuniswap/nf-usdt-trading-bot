import os
from web3 import Web3
from dotenv import load_dotenv
import time

load_dotenv()
w3 = Web3(Web3.HTTPProvider(os.getenv("ALCHEMY_URL")))
if not w3.is_connected():
    print("Cannot connect to Polygon!")
    exit()

ACCOUNT = w3.eth.account.from_key(os.getenv("PRIVATE_KEY")).address
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

NF = "0x1F4cb3949F7f5eeE736E271D07CC6ff63098bEaE"
USDT = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
POOL = "0x9657655103F382490C4A70ebc8761c5c6dc9BEC5"
ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"

ERC20_ABI = [{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
POOL_ABI = [{"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"}]
ROUTER_ABI = [{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct ISwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}]

nf = w3.eth.contract(address=NF, abi=ERC20_ABI)
usdt = w3.eth.contract(address=USDT, abi=ERC20_ABI)
pool = w3.eth.contract(address=POOL, abi=POOL_ABI)
router = w3.eth.contract(address=ROUTER, abi=ROUTER_ABI)

def get_price():
    sqrt_price = pool.functions.slot0().call()[0]
    price = (sqrt_price / (2 ** 96)) ** 2 * (10 ** 12)  # USDT 6, NF 18 decimals
    return 1 / price  # NF in USDT

def approve(token, amount):
    tx = token.functions.approve(ROUTER, amount).build_transaction({
        "from": ACCOUNT, "nonce": w3.eth.get_transaction_count(ACCOUNT),
        "gas": 200000, "gasPrice": w3.to_wei("50", "gwei")
    })
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Approved: {tx_hash.hex()}")

def buy_nf(amount_usdt):
    amount = w3.to_wei(amount_usdt, "mwei")  # USDT 6 decimals
    params = (USDT, NF, 3000, ACCOUNT, int(time.time()) + 1200, amount, 0, 0)
    approve(usdt, amount)
    tx = router.functions.exactInputSingle(params).build_transaction({
        "from": ACCOUNT, "nonce": w3.eth.get_transaction_count(ACCOUNT),
        "gas": 300000, "gasPrice": w3.to_wei("50", "gwei")
    })
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Bought NF: {tx_hash.hex()}")

def sell_nf(amount_nf):
    amount = w3.to_wei(amount_nf, "ether")  # NF 18 decimals
    params = (NF, USDT, 3000, ACCOUNT, int(time.time()) + 1200, amount, 0, 0)
    approve(nf, amount)
    tx = router.functions.exactInputSingle(params).build_transaction({
        "from": ACCOUNT, "nonce": w3.eth.get_transaction_count(ACCOUNT),
        "gas": 300000, "gasPrice": w3.to_wei("50", "gwei")
    })
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Sold NF: {tx_hash.hex()}")

def trading_bot():
    buy_price = 0.05  # Adjust this if you want
    sell_price = 0.1  # Sells at 0.1 USDT as requested
    usdt_to_spend = 10
    nf_to_sell = 100

    while True:
        try:
            price = get_price()
            print(f"NF Price: {price:.6f} USDT")

            if price < buy_price:
                print(f"Buying NF (below {buy_price})")
                buy_nf(usdt_to_spend)
            elif price > sell_price:
                nf_balance = w3.from_wei(nf.functions.balanceOf(ACCOUNT).call(), "ether")
                if nf_balance >= nf_to_sell:
                    print(f"Selling NF (above {sell_price})")
                    sell_nf(nf_to_sell)
                else:
                    print(f"Not enough NF (balance: {nf_balance})")
            else:
                print("Price in middle, waiting")

            time.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

trading_bot()

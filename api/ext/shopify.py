import json
import os
from base64 import b64encode

from aiohttp import ClientSession

from api import invoices, models, utils
from api.exceptions import BitcartError
from api.ext.moneyformat import currency_table

SHOPIFY_ORDER_PREFIX = "shopify-"
SHOPIFY_KEYWORDS = ["bitcoin", "btc", "bitcartcc", "bitcart"]


class ShopifyAPIError(BitcartError):
    """Error accessing shopify API"""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class ShopifyClient:
    def __init__(self, shop_name, api_key, api_secret):
        self.api_url = shop_name if "." in shop_name else f"https://{shop_name}.myshopify.com"
        self.api_key = api_key
        self.api_secret = api_secret
        self.auth_header = b64encode(f"{api_key}:{api_secret}".encode()).decode()
        self.headers = {"Authorization": f"Basic {self.auth_header}"}

    # Check if the store can make a request to Shopify API
    def has_required_fields(self):
        required_fields = ["api_url", "api_key", "api_secret", "auth_header", "headers"]
        for field in required_fields:
            if not hasattr(self, field) or getattr(self, field) == "":
                return False
        return True

    async def request(self, method, url, **kwargs):
        final_url = os.path.join(self.api_url, "admin/api/2022-04/" + url)
        async with ClientSession(headers=self.headers) as session:
            async with session.request(method, final_url, **kwargs) as response:
                data = await response.text()
                if response.status >= 400:
                    error_msg = "Error fetching data from Shopify API"
                    error_code = response.status
                    try:
                        error_data = json.loads(data)
                        if "errors" in error_data:
                            error_msg = error_data["errors"]
                    except json.JSONDecodeError:
                        pass
                    raise ShopifyAPIError(error_msg, status_code=error_code)
                if "invalid api key or access token" in data.lower():
                    raise ShopifyAPIError("Invalid API key or access token")
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    raise ShopifyAPIError("Invalid JSON data")
                return data

    async def get_order(self, order_id):
        return (
            await self.request(
                "GET",
                (
                    f"orders/{order_id}.json?fields=id,total_price,total_outstanding,currency"
                    ",presentment_currency,transactions,financial_status"
                ),
            )
        ).get("order", {})
    
    async def get_full_order(self, order_id):
        return (
            await self.request(
                "GET",
                (
                    f"orders/{order_id}.json"
                ),
            )
        ).get("order", {})

    async def order_exists(self, order_id):
        data = await self.request("GET", f"orders/{order_id}.json?fields=id")
        return data.get("order") is not None

    async def list_transactions(self, order_id):
        return await self.request("GET", f"orders/{order_id}/transactions.json")

    async def create_transaction(self, order_id, data):
        return await self.request("POST", f"orders/{order_id}/transactions.json", json=data)

    async def getItemsStore(self):
            try:
                response = await self.request("GET", f"products.json")
                products = []
                for product in response.get("products", []):
                    product_data = {
                        "productID": product.get("id"),
                        "name": product.get("title"),
                        "image": product.get("image", {}).get("src") if product.get("image") is not None else None

                    }
                    products.append(product_data)
                return products
            except ShopifyAPIError as e:
                raise e
                return {"error": str(e)}



def get_shopify_client(store):
    shopify_settings = store.plugin_settings.shopify
    return ShopifyClient(shopify_settings.shop_name, shopify_settings.api_key, shopify_settings.api_secret)


async def shopify_invoice_update(event, event_data):
    invoice = await utils.database.get_object(models.Invoice, event_data["id"], raise_exception=False)
    if not invoice:
        return
    order_id = invoice.order_id
    if not order_id.startswith(SHOPIFY_ORDER_PREFIX):
        return
    order_id = order_id[len(SHOPIFY_ORDER_PREFIX) :]
    store = await utils.database.get_object(models.Store, invoice.store_id, raise_exception=False)
    if not store:
        return
    client = get_shopify_client(store)
    if not await client.order_exists(order_id):
        return
    if invoice.status in invoices.FAILED_STATUSES or invoice.status in invoices.PAID_STATUSES:
        success = invoice.status in invoices.PAID_STATUSES
        await update_shopify_status(client, order_id, invoice.id, invoice.currency, invoice.price, success)


async def update_shopify_status(client, order_id, invoice_id, currency, amount, success):
    currency = currency.upper()
    transactions = (await client.list_transactions(order_id)).get("transactions", [])
    base_tx = None
    for transaction in transactions:
        if any(x in transaction["gateway"].lower() for x in SHOPIFY_KEYWORDS):
            base_tx = transaction
            break
    if base_tx is None:
        return
    if currency != base_tx["currency"].upper():
        return
    kind = "capture"
    parent_id = base_tx["id"]
    status = "success" if success else "failure"
    txes_on_same_invoice = [tx for tx in transactions if tx["authorization"] == invoice_id]
    successful_txes = [tx for tx in txes_on_same_invoice if tx["status"] == "success"]
    successful_captures = [tx for tx in successful_txes if tx["kind"] == "capture"]
    refunds = [tx for tx in txes_on_same_invoice if tx["kind"] == "refund"]
    # if we are working with a non-success registration, but see that we have previously registered this invoice as a success,
    # we switch to creating a "void" transaction, which in shopify terms is a refund.
    if not success and len(successful_captures) > 0 and len(successful_captures) - len(refunds) > 0:
        kind = "void"
        parent_id = successful_captures[-1]["id"]
        status = "success"
    # if we are working with a success registration, but can see that we have already had a successful transaction saved, exit
    elif success and len(successful_captures) > 0 and len(successful_captures) - len(refunds) > 0:
        return
    await client.create_transaction(
        order_id,
        {
            "transaction": {
                "parent_id": parent_id,
                "currency": currency,
                "amount": currency_table.format_decimal(currency, amount),
                "kind": kind,
                "gateway": "BitcartCC",
                "source": "external",
                "authorization": invoice_id,
                "status": status,
            }
        },
    )

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from api.views import router




# Inicializar o cliente de teste
client = TestClient(router)

# test_example.py
""" def test_root_endpoint():
    # Caso de teste: Verificar o retorno do endpoint raiz ("/")
    userAddress = "0xE426adF329578C9d20d1C393E6e509f6174b6EE9"
    chainID = 80001
    
    with pytest.raises(HTTPException) as e:
        client.get(f"/vouchers/?userAddress={userAddress}&chainID={chainID}")
        
    assert e.value.status_code == 422
 """

"""
# Teste para o endpoint "/nft/"
async def test_get_NFT_User_endpoint():
    # Caso de teste 1: Parâmetros válidos
    userAddress = "0xE426adF329578C9d20d1C393E6e509f6174b6EE9"
    chainID = 80001
    
    response = client.get(f"/vouchers/nft/?userAddress={userAddress}&chainID={chainID}")
    
    assert response.status_code == 200
    assert response.json() is not None

    # Caso de teste 2: Parâmetros inválidos (faltando chainID)
    userAddress = "0xE426adF329578C9d20d1C393E6e509f6174b6EE9"

    with pytest.raises(HTTPException) as exc_info:
        client.get(f"/vouchers/nft/?userAddress={userAddress}&chainID={0}")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Check request parameters"

    # Caso de teste 2: Parâmetros inválidos (Endereço inválido e chainId inválido)
    userAddress = "0xE426adF3295774b6EE9"

    with pytest.raises(HTTPException) as exc_info:
        client.get(f"/vouchers/nft/?userAddress={userAddress}&chainID={0}")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Check request parameters"
"""

"""
# Teste para o endpoint "/nftClient/"
def test_get_NFT_Client_Checkout_endpoint():
    # Caso de teste 1: Parâmetros válidos
    userAddress = "0xE426adF329578C9d20d1C393E6e509f6174b6EE9"
    chainID = 80001
    storeID = "example_store"
    lineItems = "%5B%7B%22id%22%3A%22e40744cc5873793184e3882b97b0bc48%22%2C%22key%22%3A%22e40744cc5873793184e3882b97b0bc48%22%2C%22product_id%22%3A8168503279933%2C%22variant_id%22%3A44763520762173%2C%22sku%22%3A%22%22%2C%22vendor%22%3A%22NFT%20Store%20Voucher%22%2C%22title%22%3A%22Dummy%20Product%22%2C%22variant_title%22%3Anull%2C%22image_url%22%3A%22%2F%2Fcdn.shopify.com%2Fshopifycloud%2Fshopify%2Fassets%2Fcheckout%2Fproduct-blank-98d4187c2152136e9fb0587a99dfcce6f6873f3a9f21ea9135ed7f495296090f.png%22%2C%22taxable%22%3Atrue%2C%22requires_shipping%22%3Afalse%2C%22gift_card%22%3Afalse%2C%22price%22%3A%222.00%22%2C%22compare_at_price%22%3Anull%2C%22line_price%22%3A%222.00%22%2C%22properties%22%3A%7B%7D%2C%22quantity%22%3A1%2C%22grams%22%3A0%2C%22fulfillment_service%22%3A%22manual%22%2C%22applied_discounts%22%3A%5B%5D%2C%22discount_allocations%22%3A%5B%5D%2C%22tax_lines%22%3A%5B%5D%7D%5D"
    
    response = client.get(f"/vouchers/nftClient/?userAddress={userAddress}&chainID={chainID}&storeID={storeID}&lineItems={lineItems}")
    
    assert response.status_code == 200
    assert response.json() is not None

    # Caso de teste 2: Parâmetros inválidos (parâmetros que não correspondem à verdade)
    userAddress = "0xE426adF329578C9d20d1C393E6e509f6174b6EE9"
    chainID = 80001
    storeID = "example_store"
    lineItems = "example_line_items"
    
    with pytest.raises(HTTPException) as exc_info:
        client.get(f"/vouchers/nftClient/?userAddress={userAddress}&chainID={chainID}&storeID={storeID}&lineItems=")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Check request parameters"


# Teste para o endpoint "/nft/abi"
def test_get_tokens_abi_endpoint():
    response = client.get("/vouchers/nft/abi")
    
    assert response.status_code == 200
    assert response.json() is not None
    
# Teste para o endpoint "/submit/"
def test_submit_voucher_endpoint():
    # Caso de teste 1: VoucherID Inválido
    data = {
        "chainID": 80001,
        "voucherID": "example_voucher_id",
        "invoiceID": "example_invoice_id",
        "id": "example_id"
    }
    
    with pytest.raises(HTTPException) as e:
        client.post("/vouchers/submit/", json=data)
    
    assert e.value.status_code == 400
    assert e.value.detail == "tokenId should be a valid decimal or hex value"


async def test_submit_voucher_endpoint1():
    # Caso de teste 2: Parâmetros inválidos (InvoiceID Inválido)
    data = {
        "chainID": 80001,
        "voucherID": "1",
        "invoiceID": "example_invoice_id",
        "id": "example_id"
    }
    
    with pytest.raises(HTTPException) as e:
        await client.post("/vouchers/submit/", json=data)
    
    assert e.value.status_code == 404
    assert e.value.detail == "Invoice with id example_invoice_id does not exist!"


def test_submit_voucher_endpoint2():
    # Caso de teste 3: Parâmetros inválidos (PaymentID Inválido)
    data = {
        "chainID": 80001,
        "voucherID": "1",
        "invoiceID": "wbSptRkbxENQPdmlhlvwDp",
        "id": "example_id"
    }
    
    with pytest.raises(HTTPException) as e:
        client.post("/vouchers/submit/", json=data)
    
    assert e.value.status_code == 404
    assert e.value.detail == "Invoice with id example_invoice_id does not exist!"



def test_create_voucher_endpoint_valid_params():
    voucher_data = {
        "name": "Voucher Name",
        "description": "Voucher Description",
        "externalUrl": "https://example.com/voucher",
        "voucherType": "Fixed",
        "store": ["Store A", "Store B"],
        "discountValue": "10",
        "discountCurrency": "USD"
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=DeprecationWarning)
        response = client.post("/vouchers/create", json=voucher_data)
    assert response.status_code == 200
    assert response.json()  # Verifica se a resposta contém algum valor

def test_create_voucher_endpoint_valid_params():
    # Invalid discount type
    voucher_data = {
        "name": "Voucher Name",
        "description": "Voucher Description",
        "externalUrl": "https://example.com/voucher",
        "voucherType": "",
        "store": ["Store A", "Store B"],
        "discountValue": "10",
        "discountCurrency": "USD"
    }
    with pytest.raises(HTTPException) as e:
        warnings.simplefilter("ignore", category=DeprecationWarning)
        client.post("/vouchers/create", json=voucher_data)
    assert e.value.status_code == 404
    assert e.value.detail == "Invalid discount type"


# Testes para o endpoint "/shopify-products"
def test_get_shopify_products_endpoint_valid_params():
    store_ids = "AmeNJxSencsIhJichapGKRaZgoOaopHA"

    response = client.get(f"/vouchers/shopify-products?storeIds={store_ids}")
    assert response.status_code == 200
    assert response.json()  # Verifica se a resposta contém algum valor


# Testes para o endpoint "/shopify-products"
def test_get_shopify_products_endpoint_invalid_params():
    store_ids = "1324"

    with pytest.raises(HTTPException) as e:
        client.get(f"/vouchers/shopify-products?storeIds={store_ids}")
    assert e.value.status_code == 400
    assert e.value.detail == "Store not found"


# Testes para o endpoint "/shopify-products"
def test_get_shopify_products_endpoint_invalid_params1():
    store_ids = "VOZaKwuNeWoEDbAZsImurXcoNNWsIqvv"

    with pytest.raises(HTTPException) as e:
        client.get(f"/vouchers/shopify-products?storeIds={store_ids}")
    assert e.value.status_code == 403
    assert e.value.detail == "[API] This action requires merchant approval for read_products scope."

# Testes para o endpoint "/shopify-products"
def test_get_shopify_products_endpoint_invalid_params1():
    store_ids = "gUuKEVggqfCCMavHLSjfjkuHfQQslnJS"

    with pytest.raises(HTTPException) as e:
        client.get(f"/vouchers/shopify-products?storeIds={store_ids}")
    assert e.value.status_code == 400
    assert e.value.detail == "Store is not connected to Shopify"


def test_get_nft_created_endpoint_invalid_params():
    # Parâmetros inválidos (faltando "cid")
    cid = "abc123"
    with pytest.raises(HTTPException) as e:
        client.get(f"/vouchers/nft-created?cid={cid}")

    assert e.value.status_code == 422
    assert e.value.detail == "Check request parameters"

def test_get_nft_created_endpoint_valid_params():
    cid = "QmWsKkxCAW4H7V8kbvAQ1GBEaRDX5TzywdL5PTGr8giSRx"

    response = client.get(f"/vouchers/nft-created?cid={cid}")
    assert response.status_code == 200
    assert response.json()  # Verifica se a resposta contém algum valor


# Testes para o endpoint "/stats"
def test_get_stats_endpoint_valid_user():
    # Simula um usuário válido autenticado
    user_token = "d8wU3ynw_MHEwNISDmFCEvdpufV1YgdOJYAOIDoSexg"

    response = client.get("vouchers/stats", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    assert response.json()  # Verifica se a resposta contém algum valor

def test_get_stats_endpoint_invalid_user():
    # Simula um usuário inválido (sem token de autenticação)
    with pytest.raises(HTTPException) as e:
        client.get("vouchers/stats")

    assert e.value.status_code == 401
    assert e.value.detail == "Unauthorized"


def test_get_nft_by_id_valid_parameters():
    tokenID = "100"

    response = client.get(f"vouchers/{tokenID}")
    assert response.status_code == 200
    assert response.json()  # Verifica se a resposta contém algum valor


def test_get_nft_by_id_invalid_parameters():
    tokenID = "dfghjkl"

    with pytest.raises(HTTPException) as e:
        client.get(f"vouchers/{tokenID}")

    assert e.value.status_code == 400
    assert e.value.detail == "tokenId should be a valid decimal or hex value"

def test_get_nft_by_id_invalid_parameters1():
    tokenID = "234567890"

    with pytest.raises(HTTPException) as e:
        client.get(f"vouchers/{tokenID}")

    assert e.value.status_code == 422
    assert e.value.detail == "Failed to get token uri"
"""
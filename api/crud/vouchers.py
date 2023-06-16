import requests
from api.logger import get_exception_message, get_logger
from api.settings import Settings
import json
# from web3 import Web3
# from web3.middleware import geth_poa_middleware
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from api import models, utils, schemes
from api.ext.moneyformat import currency_table
import re
from decimal import Decimal
from api.ext import shopify as shopify_ext
from api.ext.shopify import ShopifyAPIError
from PIL import Image, ImageDraw, ImageFont
import io
import os
import uuid
from api.logger import get_exception_message, get_logger
from dotenv import load_dotenv
from pathlib import Path
import uuid

dotenv_path = Path('conf/.env')
load_dotenv(dotenv_path=dotenv_path)


logger = get_logger(__name__)

networks = {
    "1": {
        "chain_id": 1,
        "name": "Ethereum Mainnet",
        "alchemy_url": "eth-mainnet",
        "rpc_url": "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161",
    },
    "5": {
        "chain_id": 5,
        "name": "Goerli Testnet",
        "alchemy_url": "eth-goerli",
        "rpc_url": "https://goerli.infura.io/v3/2f5de1aaabd447988745a4ae5a90b8d5",
    },
    "137": {
        "chain_id": 137,
        "name": "Polygon Mainnet",
        "alchemy_url": "polygon-mainnet",
        "rpc_url": "https://polygon-rpc.com",
    },
    "80001": {
        "chain_id": 80001,
        "name": "Mumbai Testnet",
        "alchemy_url": "polygon-mumbai",
        "rpc_url": "https://endpoints.omniatech.io/v1/matic/mumbai/public",
    },
}

with open("smart-contract/Web3PluginABI.json") as f:
    VOUCHER_ABI = json.loads(f.read())


class TransferRequest(BaseModel):
    from_address: str
    to_address: str
    token_id: int
    chain_id: str

class ProductBasedDiscountValue():
    FREE = "Free"
    PERCENTUAL = "%"
    CURRENCY = "€$£"

class DiscountTypes:
    FIXED = "Fixed"
    ABSOLUTE = "Absolute"
    PRODUCT_BASED = "Product-based"


    async def get_discount_type(nft_metadata: dict) -> str:
        discount_type_map = {
            "Fixed": DiscountTypes.FIXED,
            "Absolute": DiscountTypes.ABSOLUTE,
            "Product-based": DiscountTypes.PRODUCT_BASED
        }

        trait_type = next((attribute['value'] for attribute in nft_metadata['metadata']['attributes'] if attribute['trait_type'] == 'Discount Type'), None)

        discount_type = discount_type_map.get(trait_type)

        if discount_type == DiscountTypes.FIXED:
            return DiscountTypes.FIXED
        elif discount_type == DiscountTypes.ABSOLUTE:
            return DiscountTypes.ABSOLUTE
        elif discount_type == DiscountTypes.PRODUCT_BASED:
            return DiscountTypes.PRODUCT_BASED
        return None

class AlchemyProvider:
    ABI = VOUCHER_ABI

    def __init__(self) -> None:
        settings = Settings()
        self.API_KEY = settings.alchemy_api_key
        self.PINATA_API_KEY = settings.pinata_api_key
        self.PINATA_API_KEY_SECRET = settings.pinata_api_secret

        # This address is the address of the smart-contract that has been deployed on the blockchain
        self.contractAddress = "0xBf48D8Cd41d58191f4D8ae62c34d99f435A74721"

        self.PINATA_BASE_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        self.PINATA_BASE_IMAGE_URL = 'https://gateway.pinata.cloud/ipfs/QmapHk4wD4qTAESXmMq7HkBEjU8RXZLguGAtpxSnXDnkWC'

        self.STOCK_CONTRACT_ADDRESS = os.getenv('STOCK_CONTRACT_ADDRESS')
        self.STOCK_TOKEN_ID = os.getenv('STOCK_TOKEN_ID')
        self.STOCK_API_URL= os.getenv('STOCK_API_URL')

    def getContract(self):
        return self.contractAddress

    """Gets the NFT contract for each NFT in the users wallet
    @param address - User wallet address
    @param chainID - User wallet chainID
    @return JSON object
    """
    # TODO: 1. Send the Chain ID from the Metamask request - Done;
    #      2. Based on Chain ID, get the NFT of that address on that chain
    #      3. See if the NFT metadata is valid and return its metadata
    #      4. If not, return a Error message
    #      5. This function shloud return the data validated and ready to display in the merchants UI

    async def getNFTByUser(self, address: str, chainID: str):
        # This means that the address has at least 1 NFT in with that address in the Blockchain
        # (with that smart-contract)
        isHolderOfCollection = await self.checkIsHolderOfCollection(address, chainID)

        if networks.get(chainID) is not None:
            userChain = networks[chainID]
            baseURL = f"https://{userChain['alchemy_url']}.g.alchemy.com/nft/v2/{self.API_KEY}/getNFTs/"

            fetchURL = f"{baseURL}?owner={address}&withMetadata=true"

            headers = {"accept": "application/json"}
            # Gets all the NFT of that wallet account
            response = requests.get(fetchURL, headers=headers)

            # Validades the NFT and checks if they are suitable to be used in the store
            parsedNFT = self.parseNFTMetadata(response.json().get("ownedNfts"), self.contractAddress.lower())

            # response.json()
            return parsedNFT
        else:
            # Return HTTP status code error
            return None
        
    def getStockNFT(self, voucherID: str, voucherAddress: str):
        print(f"voucherID: {voucherID}")
        print(f"voucherAddress: {voucherAddress}")
        #Get the stock from the userAdress Wallet 
        STOCK_TOKEN_ID = os.getenv('STOCK_TOKEN_ID')
        STOCK_API_URL= os.getenv('STOCK_API_URL')

        # Converts the Decimal ID to HEX
        # stockTokenIdHex = hex(int(STOCK_TOKEN_ID))

        # Converter o valor hexadecimal para um objeto UUID
        uuid_value = uuid.UUID(hex=voucherID[2:])
        fetchURL = f"{STOCK_API_URL}/{uuid_value}"
        response = requests.get(fetchURL)

        responseJson = response.json()
        stock = {
            "contract": {
                "address": voucherAddress
            },
            "id": {
                "tokenId": responseJson.get("id"),
                "tokenMetadata": {
                "tokenType": "ERC1155"
                }
            },
            "title": responseJson.get("personal").get("name"),
            "description": responseJson.get("club").get("name"),
            "tokenUri": {
                "gateway": "",
                "raw": ""
            },
            "media": [
                {
                "gateway": responseJson.get("club").get("logo"),
                "raw": responseJson.get("club").get("logo")
                }
            ],
            "metadata": {
                "metadata": [],
                "attributes": []
            },
        }
        return stock
    
    def getAllStocks(self, userAddress: str):
        baseUrl = f"https://polygon-mumbai.g.alchemy.com/nft/v2/{self.API_KEY}/getNFTs"
        fetchUrl = f"{baseUrl}?owner={userAddress}&contractAddresses[]={self.STOCK_CONTRACT_ADDRESS}&withMetadata=false"

        headers = {"accept": "application/json"}
        # Gets all the NFT of that wallet account
        response = requests.get(fetchUrl, headers=headers)
        nftStocks = response.json().get("ownedNfts")

        print("Alchemy Stocks")
        print(nftStocks)
        stockList = []
        for stock in nftStocks:
            voucherID = stock.get("id").get("tokenId")
            voucherAddress = stock.get("contract").get("address")
            voucherStock = self.getStockNFT(voucherID, voucherAddress)
            stockList.append(voucherStock)

        return stockList

    """
    Checks whether a wallet holds a NFT in a given collection by contract address
    @param address - User wallet address
    @param chainID - User wallet chainID
    """

    async def checkIsHolderOfCollection(self, address: str, chainID: str):

        if networks.get(chainID) is not None:
            # Gets the Chain that the user is in
            userChain = networks[chainID]
            baseURL = f"https://{userChain['alchemy_url']}.g.alchemy.com/nft/v2/{self.API_KEY}/isHolderOfCollection/"

            fetchURL = f"{baseURL}?wallet={address}&contractAddress={self.contractAddress}"
            headers = {"accept": "application/json"}

            response = requests.get(fetchURL, headers=headers)
            return response.json().get("isHolderOfCollection")
        else:
            # Chain not supported or invalid
            # Return HTTP status code error
            return None

    def parseNFTMetadata(self, NFTMetadata: str, contractAddress: str):
        # Name of the Store
        storeName = "Store 1"
        nftData = {"ownedNfts": []}
        # Loop through every NFT
        for nft in NFTMetadata:
            # Get the address from the NFT
            nftContractAddress = nft.get("contract").get("address").lower()

            # Compare both addresses
            if nftContractAddress == contractAddress:
                # We know that the NFT is from the collection
                # Check if the NFT can be used in the store by the name
                for attr in nft.get("metadata").get("attributes"):
                    if attr["trait_type"] == "Store":
                        # Checks if the Store Name is the correct one
                        if storeName in attr["value"] or True:
                            store_value = attr["value"][0]
                            # print("Store value:", store_value)
                            nftData["ownedNfts"].append(nft)

        return nftData


    """
    This method will only return the NFT Vouchers that the user can use in the checkout,
    based on the items presented on the lineItems object (from Shopify)
    """
    async def getVouchersCheckoutUser(self, userAddress: str, chainID: str, lineItems : str, storeID: str, websiteUrl: str):
        # Raw list of the NFT
        nft = await self.getNFTByUser(userAddress, chainID)

        store = await utils.database.get_object(models.Store, storeID)
        print(store.metadata)
        print(websiteUrl)
        print("==\n")

        try:
            line_items = json.loads(lineItems)
            # Continue com o processamento do objeto JSON aqui
        except ValueError:
            # Trate o erro quando a string não puder ser convertida em JSON
            logger.error("Error parsing lineItems object")
            return None
        # 
        #
        #TODO:  
        # Get the name of the Store to compare to the name of the Store Presented on the NFT
        storeName = "Store 1"

        nftData = {"ownedNfts": []}

        # ⚠️ Alterar o modo de adição do stock à lista de vouchers
        if store.metadata.get('custom_nft') == True and store.metadata.get('shopify_store_name') == websiteUrl:
            # Get the custom stock NFT
            stockNFT = self.getAllStocks(userAddress)
            if stockNFT:
                nftData['ownedNfts'].extend(stockNFT)

        # Loop through every NFT
        for nft in nft.get("ownedNfts"):
            # Get the address from the NFT
            nftContractAddress = nft.get("contract").get("address").lower()

            # Compare both addresses
            if nftContractAddress == self.contractAddress.lower():
                # We know that the NFT is from the collection
                nftAttributes = nft.get("metadata").get("attributes")

                # If the discount is either Fixed or Absolute, we can add those vouchers to the list
                discount_type_attribute = next((a for a in nftAttributes if a['trait_type'] == 'Discount Type'), None)
                if discount_type_attribute and discount_type_attribute['value'] in ['Fixed', 'Absolute']:
                    # Check if the NFT can be used in the store by the name
                    store_attribute = next((a for a in nftAttributes if a['trait_type'] == 'Store'), None)

                    if store_attribute and storeID in store_attribute['value']:
                        # Add NFT to nftData and move on to next iteration
                        nftData['ownedNfts'].append(nft)
                    continue

                # Check if the NFT can be used in the store by the name
                store_attribute = next((a for a in nftAttributes if a['trait_type'] == 'Store'), None)

                if store_attribute and storeID in store_attribute['value']:
                    # Check if any Product ID attributes have a value that matches product_id
                    product_id_attributes = [a for a in nftAttributes if a['trait_type'] == 'Product ID']

                    # ⚠️ Test Purposes
                    # product_id_attributes[0]['value'] = [8179844677949]

                    # Meaning that the NFT is Product-Based
                    if product_id_attributes:
                        matching_line_items = []

                        # Go through every item in our Shopify Cart
                        for item in line_items:
                            for a in product_id_attributes:

                                if (str(item.get("product_id")) in a.get("value")):
                                    # We can add the NFT to the nftData
                                    matching_line_items.append(item)
                        if matching_line_items:
                            # Meaning that the Voucher can be used
                            # Add the NFT to the list
                            nftData["ownedNfts"].append(nft)
        return nftData
    
    # This method gets the infotmstion of a specific Voucher/NFT
    async def getNFTVoucher(self, chainID: str, voucherID: str):
        if networks.get(chainID) is not None:
            userChain = networks[chainID]
            baseURL = f"https://{userChain['alchemy_url']}.g.alchemy.com/nft/v2/{self.API_KEY}/getNFTMetadata/"

            fetchURL = f"{baseURL}?contractAddress={self.contractAddress}&tokenId={voucherID}"

            headers = {"accept": "application/json"}
            # Gets all the NFT of that wallet account
            response = requests.get(fetchURL, headers=headers)
            if response.status_code != 200:
                # raise ValueError("Could not fetch NFT metadata")
                response.raise_for_status()
            return response.json()
        else:
            # Return HTTP status code error
            return None

    async def submitVoucher(self, chainID: str, voucherID: str, invoiceID: str, paymentID: str, voucherContract: str) -> Dict[str, Any]:

        item = await utils.database.get_object(models.Invoice, invoiceID)
        print(f"Voucher contract {voucherContract}")
        print(f"MAin contract {self.contractAddress}")
        if (voucherContract.lower() == self.contractAddress.lower()): 
            print("Voucher is from Default Contract")
            try:
                #Get the NFT voucher
                nft = await self.getNFTVoucher(chainID, voucherID)
                
                # Get the value of the "Discount Type" attribute
                discount_type = None
                discount_type = await DiscountTypes.get_discount_type(nft)

                if not discount_type:
                    return discount_type
            
                # Switch case based on discount type
                if discount_type == DiscountTypes.FIXED:
                    nftDiscountPrice = await self.applyFixedDiscount(nft, item, paymentID)
                    return nftDiscountPrice
                elif discount_type == DiscountTypes.ABSOLUTE:
                    # Do something else
                    nftDiscountPrice = await self.applyAbsoluteDiscount(nft, item, paymentID)
                    if nftDiscountPrice:
                        return nftDiscountPrice
                    return 0
                elif discount_type == DiscountTypes.PRODUCT_BASED:
                    # Do something completely different
                    nftDiscountPrice = await self.applyProductBasedDiscount(nft, item, paymentID)
                    return nftDiscountPrice
                else:
                    # Discount type is unknown
                    pass
                    return
            except requests.HTTPError as e:
                # Capturar a exceção HTTP e retorná-la
                raise HTTPException(status_code=e.response.status_code, detail= e.response.text)
        else:
            # If the voucher is from stocks we will apply a automatic 50% discount on the invoice
            print("Voucher is from Stocks contract")

            DEFAULT_DISCOUNT = 50

            percentageNumber = Decimal(DEFAULT_DISCOUNT)
            invoiceAmount = Decimal(item.price)
            discountAmount = percentageNumber * invoiceAmount / Decimal('100')

            # Get the currency on selected (MATIC, ETH) and it's rate
            found_payment = None
            for payment in item.payments:
                if payment["id"] == paymentID:
                    found_payment = payment
                    break
            if found_payment is None:
                raise HTTPException(404, "No such payment method found")
            
            rate = Decimal(found_payment['rate'])
            divisibility = Decimal(found_payment['divisibility'])
            
            price = currency_table.normalize(found_payment['currency'], Decimal(discountAmount) / rate, divisibility=divisibility)


            return price

    
    async def applyFixedDiscount(self, nft, item, paymentID):
        try:
            # Get the traity type Discount Value that has the value of the Voucher (ex: 5€)
            discount_value = next((attribute['value'] for attribute in nft['metadata']['attributes'] if attribute['trait_type'] == 'Discount Value'), None)

            value_regex = r"[-+]?\d*[.,]?\d+|\d+"   # matches any number with optional decimal places
            symbol_regex = r"[^\d.,]+"  # matches any non-digit or comma/period character

            currency_value = re.search(value_regex, discount_value).group(0)
            currency_symbol = re.search(symbol_regex, discount_value).group(0)
            currencyName = currency_table.getVoucherCurrency(currency_symbol)
            
            # ⚠️ Test purposes
            # currencyName = "USD"

            # Check if the voucher is in the same currency of the invoice (item)
            updatedVoucherValue = None
            if not item.currency == currencyName:
                # Convert the value of the NFT to the same currency as the invoice
                updatedVoucherValue = await currency_table.getCurrencyExchangeValue(item.currency, currencyName, float(currency_value))
                print(f"{str(currency_value)} {currencyName} is equivalent to {updatedVoucherValue} {item.currency} in our invoice currency.")
            else: 
                updatedVoucherValue = currency_value
                print(f"Voucher has a value of {updatedVoucherValue} {item.currency}")

            #This method will return the value to be sent in the invoice in the currency MATIC (which is the one from the smart-contracts)
            found_payment = None
            for payment in item.payments:
                if payment["id"] == paymentID:
                    found_payment = payment
                    break
            if found_payment is None:
                raise HTTPException(404, "No such payment method found")
            
            rate = Decimal(found_payment['rate'])
            divisibility = Decimal(found_payment['divisibility'])

            # Returns the price in the chosen NFT token in this case in MATIC
            price = currency_table.normalize(found_payment['currency'], Decimal(updatedVoucherValue) / rate, divisibility=divisibility)

            return price
        except (KeyError, StopIteration) as e:
            # Handle any errors that might occur
            print("Error: could not find Discount Value trait in JSON data")
            return
    
    async def applyAbsoluteDiscount(self, nft, item, paymentID):
        try:
            discount_value = next((attribute['value'] for attribute in nft['metadata']['attributes'] if attribute['trait_type'] == 'Discount Value'), None)
            if discount_value:
                match = re.search(r'\d+(\.\d+)?', discount_value).group(0)
                # This is the percentage of the discount
                percentageNumber = Decimal(match)
                invoiceAmount = Decimal(item.price)
                discountAmount = percentageNumber * invoiceAmount / Decimal('100')

                # Get the currency on selected (MATIC, ETH) and it's rate
                found_payment = None
                for payment in item.payments:
                    if payment["id"] == paymentID:
                        found_payment = payment
                        break
                if found_payment is None:
                    raise HTTPException(404, "No such payment method found")
                
                rate = Decimal(found_payment['rate'])
                divisibility = Decimal(found_payment['divisibility'])


                # Get the invoice amount and compute the discount in the currency of the invoice
                price = currency_table.normalize(found_payment['currency'], Decimal(discountAmount) / rate, divisibility=divisibility)
                # Calculate the discount of the invoice amount in the cryptocurrency selected

                # Return it's value
                return price
            return 
        except (KeyError, StopIteration) as e:
            # Handle any errors that might occur
            print("Error: could not find Discount Value trait in JSON data")
            return
    
    async def applyProductBasedDiscount(self, nft, item, paymentID):
        try:
            discountValue = next((attribute['value'] for attribute in nft['metadata']['attributes'] if attribute['trait_type'] == 'Discount Value'), None)

            print(discountValue)

            productListIDVoucher = next((attribute['value'] for attribute in nft['metadata']['attributes'] if attribute['trait_type'] == 'Product ID'), None)

            store = await utils.database.get_object(models.Store, item.store_id)

            orderID = item.order_id
            if not orderID.startswith(shopify_ext.SHOPIFY_ORDER_PREFIX):
                if bool(item.metadata):
                    # Metadata has something inside
                    line_items = item.metadata.get('lineItems', {})

                    if line_items:
                        # Loop throught the lineItems
                        discountValuePrice = 0
                        for product in line_items:
                            if(str(product.get("product_id")) in productListIDVoucher):
                                # Means that the in item from the checkout can be applied a discount with the value discount_value
                                if discountValue == ProductBasedDiscountValue.FREE:
                                    # The product is free, so the discount is the value of the product
                                    discountValuePrice += Decimal(product.get("price"))
                                elif ProductBasedDiscountValue.PERCENTUAL in discountValue:
                                    #Get the price of the item
                                    price = product.get('price', {})

                                    match = re.search(r'\d+(\.\d+)?', discountValue).group(0)
                                    # This is the percentage of the discount

                                    percentageNumber = Decimal(match)
                                    itemAmount = Decimal(price).quantize(Decimal('.01'))
                                    discountValuePrice += percentageNumber * itemAmount / Decimal('100')
                                
                                elif any(c in discountValue for c in ProductBasedDiscountValue.CURRENCY):
                                    # The discount has a monetary value like 4€ or 4£ discount in that item
                                    value_regex = r"[-+]?\d*[.,]?\d+|\d+"   # matches any number with optional decimal places
                                    symbol_regex = r"[^\d.,]+"  # matches any non-digit or comma/period character
                                    currency_value = re.search(value_regex, discountValue).group(0)
                                    currency_symbol = re.search(symbol_regex, discountValue).group(0)
                                    currencyName = currency_table.getVoucherCurrency(currency_symbol)

                                    # Check if the voucher is in the same currency of the invoice (item)
                                    updatedVoucherValue = None
                                    if not item.currency == currencyName:
                                        # Convert the value of the NFT to the same currency as the invoice
                                        updatedVoucherValue = await currency_table.getCurrencyExchangeValue(item.currency, currencyName, float(currency_value))
                                        discountValuePrice += Decimal(updatedVoucherValue)
                                        # print(f"{str(currency_value)} {currencyName} is equivalent to {updatedVoucherValue} {item.currency} in our invoice currency.")

                                    else: 
                                        updatedVoucherValue = currency_value
                                        discountValuePrice += Decimal(updatedVoucherValue)
                                        # print(f"Voucher has a value of {updatedVoucherValue} {item.currency}")
                                else:
                                    # The voucher discount is not supported
                                    return None

                        # HERE
                        found_payment = None
                        for payment in item.payments:
                            if payment["id"] == paymentID:
                                found_payment = payment
                                break
                        if found_payment is None:
                            raise HTTPException(404, "No such payment method found")
                        
                        rate = Decimal(found_payment['rate'])
                        divisibility = Decimal(found_payment['divisibility'])

                        # Returns the price in the chosen NFT token in this case in MATIC
                        price = currency_table.normalize(found_payment['currency'], Decimal(discountValuePrice) / rate, divisibility=divisibility)

                        return price
                    else:
                        return None
                else:
                    # item.metadata is empty
                    return None
                # The order is not from Shopify
                # Do the things if the order is not from Shopify
                 # TODO: The products in DEMO STORES are stored in metadata properties
            
            '''
            This code below is just for Shopify!
            '''
            orderID = orderID[len(shopify_ext.SHOPIFY_ORDER_PREFIX) :]

            store = await utils.database.get_object(models.Store, item.store_id, raise_exception=False)
            if not store:
                return
            client = shopify_ext.get_shopify_client(store)
            if not await client.order_exists(orderID):
                # Checks for the order with Shopify API
                return
            # Get the items from the checkout in shopify
            order = await client.get_full_order(orderID)
            orderItemCheckout = order.get("line_items", {})
            print("1")
            # Loop through the item cart
            discountValuePrice = 0
            for checkoutItem in orderItemCheckout:
                print("2")
                if str(checkoutItem.get("product_id")) in productListIDVoucher:
                    print("3")
                    # Means that the in item from the checkout can be applied a discount with the value discount_value
                    if discountValue == ProductBasedDiscountValue.FREE:
                        print("4")
                        # The product is free, so the discount is the value of the product
                        discountValuePrice += Decimal(checkoutItem.get("price")) * checkoutItem.get("fulfillable_quantity")

                    elif ProductBasedDiscountValue.PERCENTUAL in discountValue:
                        #Get the price of the item
                        price_set = checkoutItem.get('price_set', {})
                        shop_money = price_set.get('shop_money', {})
                        amount = shop_money.get('amount', '')
                        currency_code = shop_money.get('currency_code', '')

                        match = re.search(r'\d+(\.\d+)?', discountValue).group(0)
                        # This is the percentage of the discount
                        percentageNumber = Decimal(match)
                        itemAmount = Decimal(amount)
                        discountValuePrice += percentageNumber * itemAmount / Decimal('100')


                    elif any(c in discountValue for c in ProductBasedDiscountValue.CURRENCY):
                        # The discount has a monetary value like 4€ or 4£ discount in that item
                        value_regex = r"[-+]?\d*[.,]?\d+|\d+"   # matches any number with optional decimal places
                        symbol_regex = r"[^\d.,]+"  # matches any non-digit or comma/period character
                        currency_value = re.search(value_regex, discountValue).group(0)
                        currency_symbol = re.search(symbol_regex, discountValue).group(0)
                        currencyName = currency_table.getVoucherCurrency(currency_symbol)
                        
                        # ⚠️ Test purposes
                        # currencyName = "USD"

                        # Check if the voucher is in the same currency of the invoice (item)
                        updatedVoucherValue = None
                        if not item.currency == currencyName:
                            # Convert the value of the NFT to the same currency as the invoice
                            updatedVoucherValue = await currency_table.getCurrencyExchangeValue(item.currency, currencyName, float(currency_value))
                            discountValuePrice += Decimal(updatedVoucherValue)
                            # print(f"{str(currency_value)} {currencyName} is equivalent to {updatedVoucherValue} {item.currency} in our invoice currency.")

                        else: 
                            updatedVoucherValue = currency_value
                            discountValuePrice += Decimal(updatedVoucherValue)
                            # print(f"Voucher has a value of {updatedVoucherValue} {item.currency}")
                    else:
                        # The voucher discount is not supported
                        return None

            found_payment = None
            for payment in item.payments:
                if payment["id"] == paymentID:
                    print("5")
                    found_payment = payment
                    break
            if found_payment is None:
                raise HTTPException(404, "No such payment method found")
            
            rate = Decimal(found_payment['rate'])
            divisibility = Decimal(found_payment['divisibility'])

            # Returns the price in the chosen NFT token in this case in MATIC
            price = currency_table.normalize(found_payment['currency'], Decimal(discountValuePrice) / rate, divisibility=divisibility)

            return price
            
        except (KeyError, StopIteration) as e:
            # Handle any errors that might occur
            print("Error: could not find Discount Value trait in JSON data")
            return
        
    async def createImageVoucher(self, voucher):
        # Fetch the image from BASE URL
        response = requests.get(self.PINATA_BASE_IMAGE_URL)
        img = Image.open(io.BytesIO(response.content))

        font_size = 110
        if voucher.voucherType == schemes.DiscountTypes.FIXED:
            currencySymbol = currency_table.get_currency_data(voucher.discountCurrency)["symbol"]
            text = f"{voucher.discountValue} {currencySymbol}"
        elif voucher.voucherType == schemes.DiscountTypes.PRODUCT_BASED:
            text = f"Discount Product \n{voucher.discountValue}"
            font_size = 90
        else:
            text = voucher.discountValue

        font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../fonts/Poppins/Poppins-Bold.ttf"))

    
        font_color = (255, 255, 255)

        # Create a PIL ImageDraw object
        draw = ImageDraw.Draw(img)
        # Get the font object and calculate the text size
        font = ImageFont.truetype(font_path, font_size)
        text_width, text_height = draw.textsize(text, font)

        # Calculate the position of the text in the bottom-center of the image
        img_width, img_height = img.size
        text_x = (img_width - text_width) // 2
        text_y = img_height - text_height - 40 # Change the value to adjust the text position

        draw.text((text_x, text_y), text, font=font, fill=font_color)

        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        fileUUID = str(uuid.uuid4())
        print(fileUUID)
        filename = f"{voucher.voucherType}-{fileUUID}.png"
        files = [
            ('file', (filename, io.BytesIO(img_bytes)))
        ]

        headers = {
            "pinata_api_key": self.PINATA_API_KEY,
            "pinata_secret_api_key": self.PINATA_API_KEY_SECRET,
        }

        # Send the request
        response = requests.post(self.PINATA_BASE_URL, headers=headers, files=files)

        # Print the response content
        response_json = response.json()
        ipfs_hash = response_json['IpfsHash']


        return ipfs_hash
    
    async def createJSONVoucher(self, imageCID: str, voucher):
        imageURL = f"https://gateway.pinata.cloud/ipfs/{imageCID}"


        if voucher.voucherType == schemes.DiscountTypes.FIXED:
            currencySymbol = currency_table.get_currency_data(voucher.discountCurrency)["symbol"]
            
            discountValue = f"{voucher.discountValue}{currencySymbol}"        

            attributes = [
                {"trait_type": "Discount Type", "value": voucher.voucherType},
                {"trait_type": "Discount Value", "value": discountValue},
                {"trait_type": "Product", "value": "All Products"},
                {"trait_type": "Store", "value": voucher.store}
            ]
            
        elif voucher.voucherType == schemes.DiscountTypes.ABSOLUTE:
            attributes = [
                {"trait_type": "Discount Type", "value": voucher.voucherType},
                {"trait_type": "Discount Value", "value": voucher.discountValue},
                {"trait_type": "Product", "value": ["All"]},
                {"trait_type": "Store", "value": voucher.store}
            ]
        elif voucher.voucherType == schemes.DiscountTypes.PRODUCT_BASED:
            attributes = [
                {"trait_type": "Discount Type", "value": voucher.voucherType},
                {"trait_type": "Discount Value", "value": voucher.discountValue},
                {"trait_type": "Product", "value": ""},
                {"trait_type": "Store", "value": voucher.store},
                {"trait_type": "Product ID", "value": voucher.productsID}
            ]
        else:
            raise HTTPException(status_code=404, detail="Invalid discount type")

        data = {
            "image" : imageURL,
            "external_url" : voucher.externalUrl,
            "name": voucher.name,
            "description": voucher.description,
            "attributes": attributes
        }

        json_data = json.dumps(data, indent=4)
        url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

        headers = {
            "Content-Type": "application/json",
            "pinata_api_key": self.PINATA_API_KEY,
            "pinata_secret_api_key": self.PINATA_API_KEY_SECRET,
        }
        filename = f"{voucher.voucherType}-JSON-{str(uuid.uuid4())}.json"
        payload = json.dumps({
            "pinataMetadata": {
                "name": filename,
            },
            "pinataContent": json.loads(json_data)
        })
        response = requests.request("POST", url, headers=headers, data=payload)
        response_json = response.json()
        ipfs_hash = response_json['IpfsHash']
        return ipfs_hash
        
    async def getStoreProducts(self, store_id):
        store = await utils.database.get_object(models.Store, store_id, raise_exception=False)
        if not store:
            return {"error": "Store not found", "status_code": 400}
        client = shopify_ext.get_shopify_client(store)
        if not client or not client.has_required_fields():
            # Means that the store is not connected to Shopify
            return {"error": "Store is not connected to Shopify", "status_code": 400}
        try:
            storeProducts = await client.getItemsStore()

        except ShopifyAPIError as e:
            # Handle the Shopify API error here
            return {"error": str(e), "status_code": e.status_code}
        
        # Process the store products here
        return storeProducts

    def getVoucherCreatedByCID(self, cid: str):
        url = f"https://gateway.pinata.cloud/ipfs/{cid}"
        try:
            response = requests.get(url)
            response.raise_for_status()  # Lança uma exceção se a resposta HTTP não for bem-sucedida (código >= 400)
            response_json = response.json()
            return response_json
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching voucher information with CID")
            return

    
    def getStatsVoucher(self, address: str):

        baseURL = f"https://polygon-mumbai.g.alchemy.com/nft/v3/{self.API_KEY}/getNFTsForOwner/"

        fetchURL = f"{baseURL}?owner={address}&contractAddresses[]={self.contractAddress}&withMetadata=false&pageSize=100"
        headers = {"accept": "application/json"}

        try: 
            response = requests.get(fetchURL, headers=headers)
            response.raise_for_status()  # Raise an exception for non-successful status codes
            countNFT = response.json().get("totalCount", 0)
            return countNFT
        except requests.exceptions.RequestException as e:
            print("Request error:", e.response.text)
            logger.error(f"Error fetching the number of voucher for address {address}:\n{get_exception_message(e)}")
        except Exception as e:
            print("Error:", e)
            logger.error(f"Unknown error occurred:\n{get_exception_message(e)}")
        return 0


    async def getNFTByID(self, tokenId: str):
        baseURL = f"https://polygon-mumbai.g.alchemy.com/nft/v2/{self.API_KEY}/getNFTMetadata"

        fetchURL = f"{baseURL}?contractAddress={self.contractAddress}&tokenId={tokenId}"

        headers = {"accept": "application/json"}

        try: 
            response = requests.get(fetchURL, headers=headers)
            response.raise_for_status()

        
        except requests.HTTPError as e:
            raise HTTPException(status_code=e.response.status_code, detail= e.response.text)
        
        nftDetail = response.json()
        return nftDetail
    
    def checkVoucherContract(self, contract: str) -> bool:
        if contract.lower() == self.STOCK_CONTRACT_ADDRESS.lower():
            return True
        return False


    '''def checkFunction(self, address: str, chainID: str):
        if networks.get(chainID) is not None:
            # Gets the Chain that the user is in
            userChain = networks[chainID]
            web3 = Web3(Web3.HTTPProvider(userChain["rpc_url"]))
            web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            contract = web3.eth.contract(address=self.contractAddress, abi=self.ABI)

            token_id = 7
            metadata = self.get_metadata(token_id, address, contract)
            return metadata
        else:
            return None
        
    # Test function to get Metadata
    def get_metadata(self, token_id, sender_address, contract):
        # call the validateOwnership function to check if the sender owns the token
        is_owner = contract.functions.validateOwnership(token_id).call({"from": sender_address})
        if not is_owner:
            raise ValueError("Caller is not the owner of the token!")

        # call the getMetadata function to get the metadata for the token
        metadata = contract.functions.getMetadata(token_id).call({"from": sender_address})
        return metadata
        '''

import requests
from api.logger import get_exception_message, get_logger
from dotenv import load_dotenv
from api.settings import Settings
import json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from fastapi import HTTPException
from pydantic import BaseModel


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


class AlchemyProvider:
    ABI = VOUCHER_ABI

    def __init__(self) -> None:
        settings = Settings()
        self.API_KEY = settings.alchemy_api_key

        # This address is the address of the smart-contract that has been deployed on the blockchain
        self.contractAddress = "0xBf48D8Cd41d58191f4D8ae62c34d99f435A74721"

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
                        if storeName in attr["value"]:
                            store_value = attr["value"][0]
                            # print("Store value:", store_value)
                            nftData["ownedNfts"].append(nft)

        return nftData


    """
    This method will only return the NFT Vouchers that the user can use in the checkout,
    based on the items presented on the lineItems object (from Shopify)
    """
    async def getVouchersCheckoutUser(self, userAddress: str, chainID: str, lineItems : str):
        # Raw list of the NFT
        nft = await self.getNFTByUser(userAddress, chainID)
        line_items = json.loads(lineItems)


        # TODO Get the name of the Store to compare to the name of the Store Presented on the NFT
        storeName = "Store 1"

        nftData = {"ownedNfts": []}

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
                    # Add NFT to nftData and move on to next iteration
                    nftData['ownedNfts'].append(nft)
                    continue

                # Check if the NFT can be used in the store by the name
                store_attribute = next((a for a in nftAttributes if a['trait_type'] == 'Store'), None)

                if store_attribute and storeName in store_attribute['value']:
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
                                if (item.get("product_id") in a.get("value")):
                                    # We can add the NFT to the nftData
                                    matching_line_items.append(item)
                        if matching_line_items:
                            # Meaning that the Voucher can be used
                            # Add the NFT to the list
                            nftData["ownedNfts"].append(nft)
        return nftData

    def checkFunction(self, address: str, chainID: str):
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

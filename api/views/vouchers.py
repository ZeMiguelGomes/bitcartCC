from fastapi import APIRouter, HTTPException, Query, Security
from api import crud, utils, models, schemes
from api.crud.vouchers import AlchemyProvider, TransferRequest
from typing import Union, List
import json


router = APIRouter()


@router.get("/")
async def root(userAddress: str, chainID: int):
    alchemyProvider = AlchemyProvider()
    nft = alchemyProvider.checkFunction(userAddress, str(chainID))
    if nft == None:
        raise HTTPException(422, "Check request parameters")
    return nft
    # return {"message": "Hello World"}


# Change to getNFTS
@router.get("/nft/")
async def get_NFT_User(userAddress: str, chainID: int):
    alchemyProvider = AlchemyProvider()

    # This method only returns the valid NFT in the user's wallet
    nft = await alchemyProvider.getNFTByUser(userAddress, str(chainID))
    if nft == None:
        raise HTTPException(422, "Check request parameters")
    return nft


@router.get("/nftClient/")
async def get_NFT_Client_Checkout(userAddress: str, chainID: int, storeID: str, lineItems: str = Query(None)):
    alchemyProvider = AlchemyProvider()
    # line_items = json.loads(lineItems)

    # This method only returns the NFT that the client can use in the Checkout
    nft = await alchemyProvider.getVouchersCheckoutUser(userAddress, str(chainID), lineItems, storeID)

    if nft == None:
        raise HTTPException(422, "Check request parameters")
    return nft


@router.get("/nft/abi")
async def get_tokens_abi():
    alchemyProvider = AlchemyProvider()
    contract = alchemyProvider.getContract()

    response = {"contractAddress": contract, "ABI": AlchemyProvider().ABI}

    return response


@router.post("/submit/")
async def submit_voucher(data: schemes.SubmitVoucher):
    alchemyProvider = AlchemyProvider()

    # This method only returns the valid NFT in the user's wallet
    nft = await alchemyProvider.submitVoucher(str(data.chainID), data.voucherID, data.invoiceID, data.id)
    if nft == None:
        raise HTTPException(422, "Check request parameters")
    return nft


@router.post("/create")
async def create_voucher(voucher: Union[schemes.FixedVoucher, schemes.ProductBasedVoucher, schemes.AbsoluteVoucher]):
    alchemyProvider = AlchemyProvider()
    print(voucher)
    print(type(voucher))  # print the class of the voucher object

    print("\n\n")
    # Create the image of the voucher and return the CID
    voucherImageCID = await alchemyProvider.createImageVoucher(voucher)

    # With the image CID, post all the info to PINATA and get the CID of the json file
    voucherJSONCID = await alchemyProvider.createJSONVoucher(voucherImageCID, voucher)
    if voucherJSONCID:
        return voucherJSONCID
    else:
        raise HTTPException(422, "Check request parameters")


@router.get("/shopify-products")
async def getShopifyProducts(storeIds: str):
    alchemyProvider = AlchemyProvider()
    data = await alchemyProvider.getStoreProducts(storeIds)

    if isinstance(data, dict) and "error" in data:
        raise HTTPException(status_code=data.get("status_code", 500), detail=data["error"])
    return data


# TODO:
# 1-> Create a endpoint that takes a list of stores and return its shopify products
# 2-> For each store get the shopify client and call the getItemsStore method


@router.get("/nft-created")
async def getNFTCreated(cid: str):
    alchemyProvider = AlchemyProvider()
    data = alchemyProvider.getVoucherCreatedByCID(cid)
    return data

@router.get("/stats")
async def getStats(address:str, user: models.User = Security(utils.authorization.auth_dependency, scopes=["full_control"]), ):
    alchemyProvider = AlchemyProvider()
    data = alchemyProvider.getStatsVoucher(address)
    return data

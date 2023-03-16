from fastapi import APIRouter, HTTPException, Query
from api import crud, utils, models, schemes
from api.crud.vouchers import AlchemyProvider, TransferRequest
from typing import Optional
from typing import Dict
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


@router.get("/nft/")
async def get_NFT_User(userAddress: str, chainID: int):
    alchemyProvider = AlchemyProvider()

    # This method only returns the valid NFT in the user's wallet
    nft = await alchemyProvider.getNFTByUser(userAddress, str(chainID))
    if nft == None:
        raise HTTPException(422, "Check request parameters")
    return nft

@router.get("/nftClient/")
async def get_NFT_Client_Checkout(userAddress: str, chainID: int, lineItems : str = Query(None)):
    alchemyProvider = AlchemyProvider()
    #line_items = json.loads(lineItems)

    # This method only returns the NFT that the client can use in the Checkout
    nft = await alchemyProvider.getVouchersCheckoutUser(userAddress, str(chainID), lineItems)

    if nft == None:
        raise HTTPException(422, "Check request parameters")
    return nft



@router.get("/nft/abi")
async def get_tokens_abi():
    alchemyProvider = AlchemyProvider()
    contract = alchemyProvider.getContract();

    response = {
        'contractAddress': contract,
        'ABI': AlchemyProvider().ABI
    }

    return response

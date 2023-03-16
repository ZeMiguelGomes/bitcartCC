// SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;

import "@openzeppelin/contracts@4.8.1/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts@4.8.1/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts@4.8.1/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts@4.8.1/token/ERC721/extensions/ERC721Burnable.sol";
import "@openzeppelin/contracts@4.8.1/access/Ownable.sol";
import "@openzeppelin/contracts@4.8.1/utils/Counters.sol";


contract Web3Plugin is ERC721, ERC721Enumerable, ERC721URIStorage, ERC721Burnable, Ownable {
    using Counters for Counters.Counter;

    Counters.Counter private _tokenIdCounter;

    constructor() ERC721("Web3PPlugin", "W3Plugin") {
        //Start the token increment in 1 not in 0
        _tokenIdCounter.increment();
    }

    //Only the owner is able to Mint new NFTs
    function safeMintOwner(address to, string memory uri) public onlyOwner {
        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();
        _mint(to, tokenId);
        _setTokenURI(tokenId, uri);
    }

    function safeMint(address to, string memory uri) public{
        //require(msg.value >= MIN_MINT_PRICE, "Not enought Ether sent");
        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();

        _mint(to, tokenId); 
        _setTokenURI(tokenId, uri);
    }

    function safeTransfer(address from, address to, uint256 tokenId) public {
        require(validateOwnership(tokenId), "Caller is not the owner of the token!");
        safeTransferFrom(from, to, tokenId);
    }

    // This function takes a tokenId parameter and returns a boolean value indicating whether
    // the caller of the function is the owner of the specified token.

    function validateOwnership(uint256 tokenId) public view returns(bool) {
        return ownerOf(tokenId) == msg.sender;
    }

    function getMetadata(uint256 tokenId) public view returns(string memory) {
        require(validateOwnership(tokenId), "Caller is not the owner of the token!");

        // Get the metadata for the specified token ID with the function tokenURI
        string memory tokenMetadata = tokenURI(tokenId);

        return tokenMetadata;
    }

    // The following functions are overrides required by Solidity.

    function _beforeTokenTransfer(address from, address to, uint256 tokenId, uint256 batchSize)
        internal
        override(ERC721, ERC721Enumerable)
    {
        super._beforeTokenTransfer(from, to, tokenId, batchSize);
    }

    function burnToken(uint256 tokenId) public {

        //Checks if the token exists
        require(_exists(tokenId), "Token does not exist");

        //Only the Owner of the token can burn the token
        require(ownerOf(tokenId) == msg.sender, "Not the owner of the token");

        _burn(tokenId);
    }

    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
    }

    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721Enumerable)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    function withdraw() public onlyOwner(){
        // Allows the owner to withdraw the balance
        require(address(this).balance > 0, "Balance is zero!");
        payable(owner()).transfer(address(this).balance);
    }
}
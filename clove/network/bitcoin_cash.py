from clove.network.base import BaseNetwork


class BitcoinCash(BaseNetwork):
    """
    Class with all the necessary BCH network information based on
    https://github.com/Bitcoin-ABC/bitcoin-abc/blob/master/src/chainparams.cpp
    (date of access: 01/18/2018)
    """
    name = 'bitcoin-cash'
    symbols = ('BCH', )
    seeds = (
        'seed.bitcoinabc.org',
        'seed-abc.bitcoinforks.org',
        'btccash-seeder.bitcoinunlimited.info',
        'seed.bitprim.org',
        'seed.deadalnix.me',
        'seeder.criptolayer.net',
    )
    port = 8333


class TestNetBitcoinCash(BitcoinCash):
    """
    Class with all the necessary BCH testing network information based on
    https://github.com/Bitcoin-ABC/bitcoin-abc/blob/master/src/chainparams.cpp
    (date of access: 01/18/2018)
    """
    name = 'test-bitcoin-cash'
    seeds = (
        'testnet-seed.bitcoinabc.org',
        'testnet-seed-abc.bitcoinforks.org',
        'testnet - seed.bitprim.org',
        'testnet-seed.deadalnix.me',
        'testnet-seeder.criptolayer.net',
    )
    port = 18333

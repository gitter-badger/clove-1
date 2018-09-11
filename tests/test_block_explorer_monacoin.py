from unittest.mock import patch

from clove.network import Monacoin
from clove.network.bitcoin.utxo import Utxo


monacoin_utxo_response = [
  {
    "txid": "e0832ca854e4577cab20413013d6251c4a426022112d9ff222067bb5d8b6b723",
    "vout": 0,
    "scriptPubKey": {
      "asm": "OP_DUP OP_HASH160 098671104a3dd5b8eb1559929221d946073a34ba OP_EQUALVERIFY OP_CHECKSIG",
      "hex": "76a9143804c5840717fb1c5c8ac0bd2726556a51e91fcd99ac",
      "type": "pubkeyhash",
      "address": "M8mXNKtwFoW765V8VEbhZ8TNCqywFr25in"
    },
    "value": 90000070
  },
  {
    "txid": "308b997d8583aa48a7b265246eb76e5d030495468bbb87989606aea769b03600",
    "vout": 1,
    "scriptPubKey": {
      "asm": "OP_DUP OP_HASH160 098671104a3dd5b8eb1559929221d946073a34ba OP_EQUALVERIFY OP_CHECKSIG",
      "hex": "76a9143804c5840717fb1c5c8ac0bd2726556a51e91fcd99ac",
      "type": "pubkeyhash",
      "address": "M8mXNKtwFoW765V8VEbhZ8TNCqywFr25in"
    },
    "value": 15500105
  },
]

expected_utxo = [
    Utxo(
        tx_id='e0832ca854e4577cab20413013d6251c4a426022112d9ff222067bb5d8b6b723',
        vout=0,
        value=0.9000007,
        tx_script='76a9143804c5840717fb1c5c8ac0bd2726556a51e91fcd99ac'
    ),
    Utxo(
        tx_id='308b997d8583aa48a7b265246eb76e5d030495468bbb87989606aea769b03600',
        vout=1,
        value=0.15500105,
        tx_script='76a9143804c5840717fb1c5c8ac0bd2726556a51e91fcd99ac'
    )
]
expected_utxo_dicts = [utxo.__dict__ for utxo in expected_utxo]


@patch('clove.block_explorer.monacoin.clove_req_json', return_value=monacoin_utxo_response)
def test_getting_utxo(json_response):
    network = Monacoin()
    address = 'testaddress'
    amount = 1.0
    assert [utxo.__dict__ for utxo in network.get_utxo(address, amount)] == expected_utxo_dicts
    assert json_response.call_args[0][0].startswith('https://mona.chainseeker.info/api/v1/utxos/')

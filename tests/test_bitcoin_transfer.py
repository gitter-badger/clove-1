from datetime import datetime, timedelta

from bitcoin.core import CTransaction, b2x, script
from freezegun import freeze_time
from pytest import raises

from clove.network.bitcoin import BitcoinTestNet
from clove.network.bitcoin.transaction import BitcoinAtomicSwapTransaction
from clove.utils.bitcoin import to_base_units


def test_swap_contract(alice_wallet, bob_wallet):
    transaction = BitcoinAtomicSwapTransaction(
        BitcoinTestNet(),
        alice_wallet.address,
        bob_wallet.address,
        0.5,
        solvable_utxo=[]
    )
    transaction.set_locktime(number_of_hours=48)
    transaction.generate_hash()
    transaction.build_atomic_swap_contract()
    assert transaction.contract.is_valid()


def test_transaction_signing(unsigned_transaction):
    transaction = unsigned_transaction
    first_script_signature = transaction.tx.vin[0].scriptSig
    transaction.sign()
    second_first_script_signature = transaction.tx.vin[0].scriptSig
    assert first_script_signature != second_first_script_signature


def test_transaction_signing_with_default_wallet(alice_wallet, unsigned_transaction):
    transaction = unsigned_transaction
    unsigned_transaction.solvable_utxo[0].wallet = None
    with raises(
        RuntimeError,
        match="Cannot sign transaction without a wallet."
    ):
        transaction.sign()

    first_script_signature = transaction.tx.vin[0].scriptSig
    transaction.sign(alice_wallet)
    second_first_script_signature = transaction.tx.vin[0].scriptSig
    assert first_script_signature != second_first_script_signature


def test_show_details(signed_transaction):
    details = signed_transaction.show_details()

    assert type(details) is dict

    str_fields = (
        'contract',
        'contract_transaction',
        'transaction_hash',
        'recipient_address',
        'refund_address',
        'secret',
        'secret_hash',
        'size_text',
        'value_text',
        'fee_text',
        'fee_per_kb_text',
    )

    date_fields = (
        'locktime',
    )

    int_fields = (
        'size',
    )

    float_fields = (
        'value',
        'fee',
        'fee_per_kb',
    )

    for field in str_fields:
        assert type(details[field]) is str, 'not a string'
        assert len(details[field]), 'empty string'

    for field in date_fields:
        assert type(details[field]) is datetime, 'not a datetime'

    for field in float_fields:
        assert type(details[field]) is float, 'not a float'

    assert details['value'] == signed_transaction.value
    assert details['value_text'] == '0.70000000 BTC'

    assert details['fee_per_kb_text'].endswith('/ 1 kB')
    assert details['size_text'].endswith('bytes')

    assert sorted(details.keys()) == sorted(str_fields + date_fields + int_fields + float_fields)


def test_transaction_fee(unsigned_transaction):

    assert type(unsigned_transaction.size) == int

    unsigned_transaction.fee_per_kb = 0.002
    unsigned_transaction.add_fee()
    assert type(unsigned_transaction.fee) == float
    assert unsigned_transaction.fee < 1, 'Transaction fee should be in main units'

    change_without_fee = unsigned_transaction.tx.vout[1].nValue
    unsigned_transaction.add_fee()
    change_with_fee = unsigned_transaction.tx.vout[1].nValue

    assert change_without_fee - to_base_units(unsigned_transaction.fee) == change_with_fee
    assert unsigned_transaction.tx.serialize()


def test_audit_contract(signed_transaction):
    btc_network = BitcoinTestNet()
    transaction_details = signed_transaction.show_details()

    contract = btc_network.audit_contract(
        transaction_details['contract'],
        transaction_details['contract_transaction']
    )
    contract_details = contract.show_details()

    assert contract.locktime == signed_transaction.locktime.replace(microsecond=0)

    contract_details.pop('locktime')

    for field in contract_details.keys():
        assert contract_details[field] == transaction_details[field]


def test_audit_contract_empty_transaction():
    btc_network = BitcoinTestNet()
    tx = b2x(CTransaction().serialize())

    with raises(
        ValueError, match='Given transaction has no outputs.'
    ):
        btc_network.audit_contract('', tx)


def test_audit_contract_invalid_transaction(signed_transaction):
    btc_network = BitcoinTestNet()
    signed_transaction.tx.vout.pop(0)
    transaction_details = signed_transaction.show_details()

    with raises(
        ValueError, match='Given transaction is not a valid contract.'
    ):
        btc_network.audit_contract(transaction_details['contract'], transaction_details['contract_transaction'])


def test_audit_contract_non_matching_contract(signed_transaction):
    btc_network = BitcoinTestNet()
    transaction_details = signed_transaction.show_details()

    contract = script.CScript([script.OP_TRUE]).hex()

    with raises(
        ValueError, match='Given transaction is not a valid contract.'
    ):
        btc_network.audit_contract(contract, transaction_details['contract_transaction'])


def test_redeem_transaction(bob_wallet, signed_transaction):
    btc_network = BitcoinTestNet()
    transaction_details = signed_transaction.show_details()

    contract = btc_network.audit_contract(
        transaction_details['contract'],
        transaction_details['contract_transaction']
    )
    redeem_transaction = contract.redeem(bob_wallet, transaction_details['secret'])
    redeem_transaction.fee_per_kb = 0.002
    redeem_transaction.add_fee_and_sign()

    assert redeem_transaction.recipient_address == bob_wallet.address
    assert redeem_transaction.value == signed_transaction.value


def test_refund_transaction(alice_wallet, signed_transaction):
    btc_network = BitcoinTestNet()
    transaction_details = signed_transaction.show_details()

    contract = btc_network.audit_contract(
        transaction_details['contract'],
        transaction_details['contract_transaction']
    )

    with freeze_time(transaction_details['locktime']):
        refund_transaction = contract.refund(alice_wallet)

    refund_transaction.fee_per_kb = 0.002
    refund_transaction.add_fee_and_sign()

    assert refund_transaction.recipient_address == alice_wallet.address
    assert refund_transaction.value == signed_transaction.value


def test_refund_not_expired_contract(alice_wallet, signed_transaction):
    btc_network = BitcoinTestNet()
    transaction_details = signed_transaction.show_details()

    contract = btc_network.audit_contract(
        transaction_details['contract'],
        transaction_details['contract_transaction']
    )

    with freeze_time(transaction_details['locktime'] - timedelta(seconds=1)):
        locktime_string = transaction_details['locktime'].strftime('%Y-%m-%d %H:%M:%S')
        with raises(
            RuntimeError, match=f"This contract is still valid! It can't be refunded until {locktime_string}."
        ):
            contract.refund(alice_wallet)


def test_participate_transaction(alice_wallet, bob_wallet, bob_utxo, signed_transaction):
    btc_network = BitcoinTestNet()
    transaction_details = signed_transaction.show_details()

    contract = btc_network.audit_contract(
        transaction_details['contract'],
        transaction_details['contract_transaction']
    )
    participate_value = 0.5
    participate_transaction = contract.participate(
        'btc', bob_wallet.address, alice_wallet.address, participate_value, bob_utxo
    )
    participate_transaction.fee_per_kb = 0.002
    participate_transaction.add_fee_and_sign()

    assert participate_transaction.sender_address == bob_wallet.address
    assert participate_transaction.recipient_address == alice_wallet.address
    assert participate_transaction.value == participate_value
    assert participate_transaction.secret_hash == signed_transaction.secret_hash
    assert participate_transaction.secret is None
    assert isinstance(participate_transaction.network, BitcoinTestNet)

    participate_transaction_details = participate_transaction.show_details()

    contract = btc_network.audit_contract(
        participate_transaction_details['contract'],
        participate_transaction_details['contract_transaction']
    )
    redeem_participate_transaction = contract.redeem(alice_wallet, transaction_details['secret'])
    redeem_participate_transaction.fee_per_kb = 0.002
    redeem_participate_transaction.add_fee_and_sign()

    assert redeem_participate_transaction.recipient_address == alice_wallet.address
    assert redeem_participate_transaction.value == participate_value


def test_extract_secret(bob_wallet, signed_transaction):
    btc_network = BitcoinTestNet()
    transaction_details = signed_transaction.show_details()

    contract = btc_network.audit_contract(
        transaction_details['contract'],
        transaction_details['contract_transaction']
    )
    redeem_transaction = contract.redeem(bob_wallet, transaction_details['secret'])
    redeem_transaction.fee_per_kb = 0.002
    redeem_transaction.add_fee_and_sign()

    redeem_details = redeem_transaction.show_details()

    secret = btc_network.extract_secret(redeem_details['transaction'])

    assert secret == transaction_details['secret']

#!/usr/bin/env python3

import pytest
from algosdk import error as algo_error
from algosdk.atomic_transaction_composer import *
from algosdk.future import transaction
from beaker import sandbox
from beaker.client.application_client import ApplicationClient

from smartcontract.contract import Ecommerce, EcommerceMessage as EM

algod_client = sandbox.get_algod_client()


@pytest.fixture
def order_amount() -> int:
    return 10000

@pytest.fixture
def admin_client(appid) -> ApplicationClient:
    admin = sandbox.get_accounts()[0]
    algod_client = sandbox.get_algod_client()
    c = ApplicationClient(
        client=algod_client,
        app=Ecommerce(),
        app_id=int(appid),
        signer=admin.signer
    )
    return c


@pytest.fixture
def seller_client(appid) -> ApplicationClient:
    seller = sandbox.get_accounts()[1]
    algod_client = sandbox.get_algod_client()
    c = ApplicationClient(
        client=algod_client,
        app=Ecommerce(),
        app_id=int(appid),
        signer=seller.signer
    )
    return c


@pytest.fixture
def buyer_client(appid) -> ApplicationClient:
    buyer = sandbox.get_accounts()[2]
    algod_client = sandbox.get_algod_client()
    c = ApplicationClient(
        client=algod_client,
        app=Ecommerce(),
        app_id=int(appid),
        signer=buyer.signer
    )
    return c


@pytest.fixture(autouse=True)
def run_around_tests(admin_client, buyer_client, seller_client):

    algod_client = algod.AlgodClient(
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "http://localhost:4001"
    )

    sp = algod_client.suggested_params()
    block_info = algod_client.block_info(sp.first)

    padmincall = (admin_client.client.account_info(admin_client.get_sender()))
    psellercall = (seller_client.client.account_info(seller_client.get_sender()))
    pbuyercall = (buyer_client.client.account_info(buyer_client.get_sender()))

    yield

    print("\n-----------------------------------")
    print(f" Start in round: {block_info['block']['rnd']}")
    poadmincall = (admin_client.client.account_info(admin_client.get_sender()))
    print(f"Balance pre admin call  {padmincall['amount']}")
    print(f"Balance post admin call {poadmincall['amount']}")
    print(f"Cost: {padmincall['amount'] - poadmincall['amount']}")

    posellercall = (seller_client.client.account_info(seller_client.get_sender()))

    print(f"\nBalance pre seller call  {psellercall['amount']}")
    print(f"Balance post seller call {posellercall['amount']}")
    print(f"Cost: {psellercall['amount'] - posellercall['amount']}")

    pobuyercall = (buyer_client.client.account_info(buyer_client.get_sender()))

    sp = algod_client.suggested_params()
    block_info = algod_client.block_info(sp.first)

    print(f"\nBalance pre seller call  {pbuyercall['amount']}")
    print(f"Balance post seller call {pobuyercall['amount']}")
    print(f"Cost: {pbuyercall['amount'] - pobuyercall['amount']}")
    print(f"Finished in round: {block_info['block']['rnd']}")
    print("\n-----------------------------------\n")


def test_admin_add_funds_earning_usdc(admin_client: ApplicationClient, usdc):
    app_client = admin_client
    amount = int(1e10)

    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn=transaction.AssetTransferTxn(
            app_client.get_sender(), sp, app_client.app_addr, amount, int(usdc)
        ),
        signer=app_client.get_signer()
    )
    r = app_client.call(
        Ecommerce.addFundsEarning,
        att=ptxn,
        token=int(usdc)
    )

    assert int(r.return_value) >= amount, "Balance USDC do not match"
    print(f"Return Result:{r.return_value}")


def test_admin_add_funds_earning_usdt(admin_client: ApplicationClient, usdt):
    app_client = admin_client
    amount = int(2e10)

    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn=transaction.AssetTransferTxn(
            app_client.get_sender(), sp, app_client.app_addr, amount, int(usdt)
        ),
        signer=app_client.get_signer()
    )
    r = app_client.call(
        Ecommerce.addFundsEarning,
        att=ptxn,
        token=int(usdt)
    )
    assert r.return_value >= amount, "Balance USDT do not match"
    print(f"Return Result:{r.return_value}")


def test_admin_withdraw_earnings_usdc(admin_client: ApplicationClient, usdc):
    app_client = admin_client
    amount = int(1e10)
    pre_balance = int(app_client.get_application_state()["earning\x01"]) or 0
    r = app_client.call(
        Ecommerce.withdrawEarnings,
        amount=amount,
        token=int(usdc)
    )
    balance = pre_balance - amount
    assert int(r.return_value) == balance, "Balance USDC do not match"
    print(f"Return Result:{r.return_value}")


def test_admin_withdraw_earnings_usdt(admin_client: ApplicationClient, usdt):
    app_client = admin_client
    amount = int(2e10)
    pre_balance = int(app_client.get_application_state()["earning\x02"]) or 0
    r = app_client.call(
        Ecommerce.withdrawEarnings,
        amount=amount,
        token=int(usdt)
    )
    balance = pre_balance - amount
    assert int(r.return_value) == balance, "Balance USDT do not match"
    print(f"Return Result:{r.return_value}")


def test_seller_buy_license_incorrect_amount(seller_client: ApplicationClient):
    app_client = seller_client
    lni = int(app_client.get_application_state()["lni"])
    amount = int(app_client.get_application_state()["lp"]) - int(100)
    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            app_client.get_sender(),
            sp,
            app_client.app_addr,
            amount
        ),
        signer=app_client.get_signer()
    )

    with pytest.raises(Exception) as e:
        r = app_client.call(
            Ecommerce.payLicense,
            p=ptxn,
            a=lni
        )
    print("Incorrect amount")
    assert e.type is algo_error.AlgodHTTPError
    print(e)


def test_seller_buy_license(seller_client: ApplicationClient):
    print("Running test for Buying License")
    app_client = seller_client
    lni = int(app_client.get_application_state()["lni"])
    amount = int(app_client.get_application_state()["lp"])
    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            app_client.get_sender(),
            sp,
            app_client.app_addr,
            amount
        ),
        signer=app_client.get_signer()
    )
    # optin license nft

    r = app_client.call(
        Ecommerce.payLicense,
        p=ptxn,
        a=lni
    )
    print(r.return_value)
    assert r.return_value == EM.OK_PAYMENT_SUCCESSFULL, "Unable to pay license"


def test_buyer_pay_order_usdc(buyer_client: ApplicationClient, usdc, order_amount):
    app_client = buyer_client
    sp = algod_client.suggested_params()


    otxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            app_client.get_sender(), sp, app_client.app_addr, int(1e5)
        ),
        signer=app_client.get_signer()
    )
    ptxn = TransactionWithSigner(
        txn=transaction.AssetTransferTxn(
            app_client.get_sender(), sp, app_client.app_addr, order_amount, int(usdc)
        ),
        signer=app_client.get_signer()
    )
    r = app_client.call(
        Ecommerce.payOrder,
        oracle_pay=otxn,
        product_pay=ptxn,
    )
    print(f"Buyer paid with usdc order::{r.return_value}")


def test_buyer_pay_order_usdt(buyer_client: ApplicationClient, usdt, order_amount):
    app_client = buyer_client
    sp = algod_client.suggested_params()

    otxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            app_client.get_sender(), sp, app_client.app_addr, int(2e5)
        ),
        signer=app_client.get_signer()
    )
    ptxn = TransactionWithSigner(
        txn=transaction.AssetTransferTxn(
            app_client.get_sender(), sp, app_client.app_addr, order_amount, int(usdt)
        ),
        signer=app_client.get_signer()
    )
    r = app_client.call(
        Ecommerce.payOrder,
        oracle_pay=otxn,
        product_pay=ptxn,
    )

    print(f"Buyer paid with usdt order::{r.return_value}")


def test_buyer_check_balance_usdt(buyer_client: ApplicationClient, usdt):
    app_client = buyer_client
    sp = algod_client.suggested_params()
    r = app_client.call(
        Ecommerce.checkUserBalance,
        a=int(usdt)
    )
    print(f"Buyer usdc balance:{r.return_value}")


def test_admin_create_order_usdc(admin_client, usdc, order_amount):
    app_client = admin_client
    nft_observer = int(admin_client.get_application_state()['oni'])
    o = {
        "seller": "TP7FTYCJRG6VDD4EJHHFTP7K5HLCTSY4EPRDHD2LQH7HG6OPCE5ZZMLD4E",
        "buyer": "WBPK76F6U2VYPSUDHSNV3BFVYOMXP4LXM32UG7PFTS7ENEOVVNQZ576RHE",
        "amount": order_amount,
        "token": int(usdc),
        "seller_state": 0,
        "buyer_state": 0
    }
    r = app_client.call(
        Ecommerce.createOrder,
        k="order_1",
        order=o,
        nft_observer=nft_observer,
        boxes=[[app_client.app_id, "order_1"]]
    )
    # assert r.return_value == "new_order_created", "The order already exist"
    print(f"Admin places the order: {r.return_value}")


def test_admin_create_duplicated_order_usdc(admin_client, usdc):
    app_client = admin_client
    nft_observer = int(admin_client.get_application_state()['oni'])
    o = {
        "seller": "TP7FTYCJRG6VDD4EJHHFTP7K5HLCTSY4EPRDHD2LQH7HG6OPCE5ZZMLD4E",
        "buyer": "WBPK76F6U2VYPSUDHSNV3BFVYOMXP4LXM32UG7PFTS7ENEOVVNQZ576RHE",
        "amount": 10000,
        "token": int(usdc),
        "seller_state": 1,
        "buyer_state": 0
    }
    r = app_client.call(
        Ecommerce.createOrder,
        k="order_2",
        order=o,
        nft_observer=nft_observer,
        boxes=[[app_client.app_id, "order_2"]]
    )
    assert r.return_value == "order_already_exist", "The order already exist"
    print(f"Failed to place the order: {r.return_value}")


def test_seller_accept_order_usdc(seller_client, usdc, al):
    app_client = seller_client

    r = app_client.call(
        Ecommerce.sellerAcceptOrder,
        k="order_1",
        license=int(al),

        boxes=[[app_client.app_id, "order_1"]]
    )
    # assert r.return_value == "new_order_created", "The order already exist"
    print(f"Return Value: {r.return_value}")


def test_seller_cancel_order_usdc(seller_client, buyer_client, usdc, al):
    app_client = seller_client
    buyer_client = buyer_client

    r = app_client.call(
        Ecommerce.sellerCancelOrder,
        k="order_1",
        license=int(al),
        b=buyer_client.get_sender(),
        boxes=[[app_client.app_id, "order_1"]]
    )

    print(f"Return Value: {r.return_value}")


def test_buyer_payout_order_usdc(buyer_client, seller_client, usdc, al):
    app_client = buyer_client

    r = app_client.call(
        Ecommerce.buyerCompleteOrder,
        k="order_1",
        s="TP7FTYCJRG6VDD4EJHHFTP7K5HLCTSY4EPRDHD2LQH7HG6OPCE5ZZMLD4E",
        boxes=[[app_client.app_id, "order_1"]],
    )
    print(f"Return Value: {r.return_value}")


def test_seller_withdraw_usdc(seller_client, usdc):
    app_client = seller_client

    r = app_client.call(
        Ecommerce.userWithdraw,
        token=int(usdc)
    )
    print(f"Return Value: {r.return_value}")

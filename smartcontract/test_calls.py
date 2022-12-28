#!/usr/bin/env python3
import json
from ast import Constant
import pytest
import sys
from algosdk.abi import ABIType
from algosdk import error as algo_error
from algosdk.atomic_transaction_composer import *
from algosdk.future import transaction
from algosdk.v2client.algod import AlgodClient
from algosdk.encoding import decode_address
from beaker import client, sandbox
from beaker.client.application_client import ApplicationClient
from pyteal import *
from algosdk import encoding
from .contract import Ecommerce, EcommerceMessage as EM

algod_client  = sandbox.get_algod_client()

@pytest.fixture
def admin_client(appid) -> ApplicationClient:
    admin = sandbox.get_accounts()[0]
    algod_client  = sandbox.get_algod_client()
    c = ApplicationClient(
        client = algod_client,
        app = Ecommerce(),
        app_id=int(appid),
        signer = admin.signer
    )
    return c
@pytest.fixture
def seller_client(appid) -> ApplicationClient:
    seller = sandbox.get_accounts()[1]
    algod_client  = sandbox.get_algod_client()
    c = ApplicationClient(
        client = algod_client,
        app = Ecommerce(),
        app_id=int(appid),
        signer = seller.signer
    )
    return c
@pytest.fixture
def buyer_client(appid) -> ApplicationClient:
    buyer = sandbox.get_accounts()[2]
    algod_client  = sandbox.get_algod_client()
    c = ApplicationClient(
        client = algod_client,
        app = Ecommerce(),
        app_id=int(appid),
        signer = buyer.signer
    )
    return c

@pytest.fixture(autouse=True)
def run_around_tests(admin_client,buyer_client,seller_client):
    padmincall = (admin_client.client.account_info(admin_client.get_sender()))
    psellercall = (seller_client.client.account_info(seller_client.get_sender()))
    pbuyercall = (buyer_client.client.account_info(buyer_client.get_sender()))

    yield
    print("\n-----------------------------------")
    poadmincall = (admin_client.client.account_info(admin_client.get_sender()))
    print(f"Balance pre admin call  {padmincall['amount']}")
    print(f"Balance post admin call {poadmincall['amount']}")
    print(f"Cost: {padmincall['amount'] - poadmincall['amount']}")

    posellercall = (seller_client.client.account_info(seller_client.get_sender()))

    print(f"\nBalance pre seller call  {psellercall['amount']}")
    print(f"Balance post seller call {posellercall['amount']}")
    print(f"Cost: {psellercall['amount'] - posellercall['amount']}")

    pobuyercall = (buyer_client.client.account_info(buyer_client.get_sender()))
    print(f"\nBalance pre seller call  {pbuyercall['amount']}")
    print(f"Balance post seller call {pobuyercall['amount']}")
    print(f"Cost: {pbuyercall['amount'] - pobuyercall['amount']}")
    print("\n-----------------------------------\n")

def test_admin_add_funds_earning_usdc(admin_client:ApplicationClient,appaddr,usdc):
    app_client =  admin_client
    amount = int(1e10)

    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn = transaction.AssetTransferTxn(
            app_client.get_sender(),sp,app_client.app_addr,amount,int(usdc)
        ),
        signer = app_client.get_signer()
    )
    r = app_client.call(
        Ecommerce.addFundsEarning,
        att = ptxn,
        token = int(usdc)
    )
    assert r.return_value == amount, "Current balance in the smartcontract must be: "+ amount
    print(f"Return Result:{r.return_value}")

def test_admin_add_funds_earning_usdt(admin_client:ApplicationClient,appaddr,usdt):
    app_client =  admin_client
    amount = int(2e10)
    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn = transaction.AssetTransferTxn(
            app_client.get_sender(),sp,app_client.app_addr,amount,int(usdt)
        ),
        signer = app_client.get_signer()
    )
    r = app_client.call(
        Ecommerce.addFundsEarning,
        att = ptxn,
        token = int(usdt)
    )
    assert r.return_value == amount, "The current balance in usdc must be (2e10)"
    print(f"Return Result:{r.return_value}")

def test_admin_withdraw_earnings_usdc(admin_client:ApplicationClient,appaddr,usdc):
    app_client =  admin_client
    amount = int(1e10)
    r = app_client.call(
        Ecommerce.withdrawEarnings,
        amount = amount,
        token = int(usdc)
    )
    assert int(r.return_value) == 0, "The current balance (USDT) in the smart contract must be zero"
    print(f"Return Result:{r.return_value}")
def test_admin_withdraw_earnings_usdt(admin_client:ApplicationClient,appaddr,usdt):
    app_client =  admin_client
    amount = int(2e10)
    r = app_client.call(
        Ecommerce.withdrawEarnings,
        amount = amount,
        token = int(usdt)
    )
    assert int(r.return_value) == 0, "The current balance (USDT) in the smart contract must be zero"
    print(f"Return Result:{r.return_value}")

def test_seller_buy_license_incorrect_amount(seller_client:ApplicationClient,al):
    app_client = seller_client
    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn = transaction.PaymentTxn(
            app_client.get_sender(),
            sp,
            app_client.app_addr,
            int(100)
        ),
        signer = app_client.get_signer()
    )


    with pytest.raises(Exception) as e:
        r = app_client.call(
            Ecommerce.payLicense,
            p =ptxn,
            a = int(al)
        )
    print("Incorrect amount")
    assert e.type is algo_error.AlgodHTTPError
    print(e)


def test_seller_buy_license(seller_client:ApplicationClient,al):
    app_client = seller_client
    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn = transaction.PaymentTxn(
            app_client.get_sender(),
            sp,
            app_client.app_addr,
            int(4000)
        ),
        signer = app_client.get_signer()
    )
    # optin license nft

    r = app_client.call(
        Ecommerce.payLicense,
        p =ptxn,
        a = int(al)
    )
    print(r.return_value)
    assert r.return_value == EM.OK_PAYMENT_SUCCESSFULL, "Unable to pay license"

def test_seller_re_buy_license(seller_client:ApplicationClient,al):
    app_client = seller_client
    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn = transaction.PaymentTxn(
            app_client.get_sender(),
            sp,
            app_client.app_addr,
            Ecommerce._seller_cost
        ),
        signer = app_client.get_signer()
    )
    # optin license nft
    with pytest.raises(Exception) as e:
        r = app_client.call(
            Ecommerce.payLicense,
            p =ptxn,
            a = int(al)
        )
    print("Cant buy more licenses")
    assert e.type is algo_error.AlgodHTTPError

def test_buyer_pay_order_usdc(buyer_client:ApplicationClient,usdc):
    app_client =  buyer_client
    sp = algod_client.suggested_params()

    otxn = TransactionWithSigner(
        txn = transaction.PaymentTxn(
            app_client.get_sender(),sp,app_client.app_addr , int(1e5)
        ),
        signer = app_client.get_signer()
    )
    ptxn = TransactionWithSigner(
        txn = transaction.AssetTransferTxn(
            app_client.get_sender(),sp,app_client.app_addr,1000,int(usdc)
        ),
        signer = app_client.get_signer()
    )
    r = app_client.call(
        Ecommerce.payOrder,
        oracle_pay=otxn,
        product_pay= ptxn,
    )
    print(f"Buyer paid with usdc order::{r.return_value}")

def test_buyer_pay_order_usdt(buyer_client:ApplicationClient,usdt):
    app_client =  buyer_client
    sp = algod_client.suggested_params()

    otxn = TransactionWithSigner(
        txn = transaction.PaymentTxn(
            app_client.get_sender(),sp,app_client.app_addr , int(2e5)
        ),
        signer = app_client.get_signer()
    )
    ptxn = TransactionWithSigner(
        txn = transaction.AssetTransferTxn(
            app_client.get_sender(),sp,app_client.app_addr,1000,int(usdt)
        ),
        signer = app_client.get_signer()
    )
    r = app_client.call(
        Ecommerce.payOrder,
        oracle_pay=otxn,
        product_pay= ptxn,
    )

    print(f"Buyer paid with usdt order::{r.return_value}")

def test_buyer_check_balance_usdt(buyer_client:ApplicationClient,usdt):
    app_client =  buyer_client
    sp = algod_client.suggested_params()
    r = app_client.call(
        Ecommerce.checkUserBalance,
        a = int(usdt)
    )
    print(f"Buyer usdc balance:{r.return_value}")

def test_admin_create_order_usdc(admin_client,usdc):
        app_client = admin_client

        o = {
            "seller": "TP7FTYCJRG6VDD4EJHHFTP7K5HLCTSY4EPRDHD2LQH7HG6OPCE5ZZMLD4E",
            "buyer":"WBPK76F6U2VYPSUDHSNV3BFVYOMXP4LXM32UG7PFTS7ENEOVVNQZ576RHE",
            "amount":100000,
            "token":int(usdc),
            "seller_state":0,
            "buyer_state":0
        }
        r = app_client.call(
            Ecommerce.createOrder,
            k="order_1",
            order = o,
            nft_observer = 15,
            boxes=[[app_client.app_id, "order_1"]]
        )
        # assert r.return_value == "new_order_created", "The order already exist"
        print(f"Admin places the order: {r.return_value}")

def test_admin_create_duplicated_order_usdc(admin_client,usdc):
        app_client = admin_client

        o = {
            "seller": "TP7FTYCJRG6VDD4EJHHFTP7K5HLCTSY4EPRDHD2LQH7HG6OPCE5ZZMLD4E",
            "buyer":"WBPK76F6U2VYPSUDHSNV3BFVYOMXP4LXM32UG7PFTS7ENEOVVNQZ576RHE",
            "amount":1000,
            "token":int(usdc),
            "seller_state":1,
            "buyer_state":0
        }
        r = app_client.call(
            Ecommerce.newOrder,
            k="order_2",
            order = o,
            boxes=[[app_client.app_id, "order_2"]]
        )
        assert r.return_value == "order_already_exist", "The order already exist"
        print(f"Failed to place the order: {r.return_value}")
def test_seller_accept_order_usdc(seller_client, usdc,al):
        app_client = seller_client

        # "seller": "TP7FTYCJRG6VDD4EJHHFTP7K5HLCTSY4EPRDHD2LQH7HG6OPCE5ZZMLD4E",

        r = app_client.call(
            Ecommerce.sellerAcceptOrder,
            k="order_1",
            license = int(al),

            boxes=[[app_client.app_id, "order_1"]]
        )
        # assert r.return_value == "new_order_created", "The order already exist"
        print(f"Return Value: {r.return_value}")

def test_seller_cancel_order_usdc(seller_client,buyer_client, usdc,al):
        app_client = seller_client
        buyer_client = buyer_client
        # "seller": "TP7FTYCJRG6VDD4EJHHFTP7K5HLCTSY4EPRDHD2LQH7HG6OPCE5ZZMLD4E",

        r = app_client.call(
            Ecommerce.sellerCancelOrder,
            k="order_1",
            license = int(al),
            b = buyer_client.get_sender(),
            boxes=[[app_client.app_id, "order_1"]]
        )

        print(f"Return Value: {r.return_value}")
def test_seller_is_seller(seller_client, usdc,al):
    app_client = seller_client

    r = app_client.call(
        Ecommerce.sellerTakeOrder,
        license = int(al)
    )
    assert r.return_value == 1, "This is a seller address"
    print(f"Return Value {r.return_value}")

def test_seller_fake_seller(buyer_client, usdc,al):
    app_client = buyer_client

    r = app_client.call(
        Ecommerce.sellerAcceptOrder,
        license = int(al)
    )

    assert r.return_value != 1, "Address is not a faker seller"
    print(f"Return Value {r.return_value}")
def test_buyer_payout_order_usdc(buyer_client,seller_client, usdc,al):
        app_client = buyer_client
        seller_client = seller_client
        r = app_client.call(
            Ecommerce.buyerCompleteOrder,
            k="order_1",
            s = "TP7FTYCJRG6VDD4EJHHFTP7K5HLCTSY4EPRDHD2LQH7HG6OPCE5ZZMLD4E",
            boxes=[[app_client.app_id, "order_1"]],
        )
        print(f"Return Value: {r.return_value}")

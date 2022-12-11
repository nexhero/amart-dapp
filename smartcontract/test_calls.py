#!/usr/bin/env python3

from ast import Constant
import pytest
import sys
from algosdk.atomic_transaction_composer import *
from algosdk.future import transaction
from algosdk.v2client.algod import AlgodClient
from algosdk.encoding import decode_address
from beaker import client, sandbox
from beaker.client.application_client import ApplicationClient
from pyteal import *
from algosdk import encoding
from .contract import Ecommerce

algod_client  = sandbox.get_algod_client()

def test_usdc(usdc, usdt):
    print(f" value of usdc:{type(usdc)}")
    print(f" value of usdt:{type(int(usdt))}")

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

def test_admin_funds_box(admin_client:ApplicationClient,appaddr,appid):
    app_client = admin_client
    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn = transaction.PaymentTxn(
            app_client.get_sender(),sp,appaddr, int(1e5)
        ),
        signer = app_client.get_signer()
    )
    r = app_client.call(
        Ecommerce.addFundBoxAlgoBalance,
        t= ptxn,
    )
    assert r.return_value == int(1e5)
    print(f"Admin deposited funds for boxes:{r.return_value}")


def test_admin_withdraw_funds_box(admin_client:ApplicationClient,appaddr):
    app_client =  admin_client

    r = app_client.call(
        Ecommerce.withdrawFundBoxAlgosBalance,
        a = int(1e4)
    )
    print(f"Admin withdraw funds for boxes:{r.return_value}")

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
    print(f"Buyer pay order::{r.return_value}")



    # def test_new_order(self,admin_acc:tuple[str,str,AccountTransactionSigner]):
    #     addr,sk,signer =  admin_acc
    #     app_client = client.ApplicationClient(self.algod_client,self.app,self.app_id,signer=signer)
    #     o = {
    #         "seller":"MSNHPFV3UYDPSSPVMJ7O3HX3CDXCIK2PUCTBB5GHBYAPLASK5TLEKP3PWI",
    #         "buyer": "RRXY3RSR2XRMJG3ZOBBTYXWLU6SKG3YJGUEEN4CC6MHOMCF4V2Q2ZYN4R4",
    #         "amount":int(1000),
    #         "token":self.USDC,
    #         "seller_state":1,
    #         "buyer_state":0
    #     }
    #     r = app_client.call(
    #         Ecommerce.newOrder,
    #         id="12313131313131231231312",
    #         order = o,
    #         boxes=[[app_client.app_id, "12313131313131231231312"]]
    #     )
    #     print(f"Admin places the order: {r.return_value}")

    # def test_complete_order(self,admin_acc:tuple[str,str,AccountTransactionSigner]):
    #     addr,sk,signer =  admin_acc
    #     app_client = client.ApplicationClient(self.algod_client,self.app,self.app_id,signer=signer)
    #     o = {
    #         "seller":"MSNHPFV3UYDPSSPVMJ7O3HX3CDXCIK2PUCTBB5GHBYAPLASK5TLEKP3PWI",
    #         "buyer": "RRXY3RSR2XRMJG3ZOBBTYXWLU6SKG3YJGUEEN4CC6MHOMCF4V2Q2ZYN4R4",
    #         "amount":int(2e10),
    #         "token":self.USDC,
    #         "seller_state":1,
    #         "buyer_state":0
    #     }
    #     r = app_client.call(
    #         Ecommerce.completeOrder,
    #         id="2432423423542352",
    #         order = o,
    #         boxes=[[app_client.app_id, "2432423423542352"]]
    #     )
    #     print(f"Order Status: {r.return_value}")

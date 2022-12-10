#!/usr/bin/env python3

from ast import Constant
import pytest
from algosdk.atomic_transaction_composer import *
from algosdk.future import transaction
from algosdk.v2client.algod import AlgodClient
from algosdk.encoding import decode_address
from beaker import client, sandbox
from beaker.client.application_client import ApplicationClient
from pyteal import *
from algosdk import encoding
from .contract import Ecommerce

class TestEcommerce:
    accounts = sandbox.get_accounts()

    USDC = 4
    USDT = 5
    algod_client:AlgodClient = sandbox.get_algod_client()
    app_id = 26
    license_id = 29
    app_addr = 'WKQ64D7YMYZUUUU7RHDCPSHZX7QM63TS2PZ32IM55Y4FEUIAYKHWFJRSLA'

    app = Ecommerce()


    @pytest.fixture
    def admin_acc(self) -> tuple[str,str,AccountTransactionSigner]:
        addr, sk = self.accounts[0].address, self.accounts[0].private_key
        return (addr,sk,self.accounts[0].signer)
    @pytest.fixture
    def seller_acc(self) -> tuple[str,str,AccountTransactionSigner]:
        addr, sk = self.accounts[1].address, self.accounts[1].private_key
        return (addr,sk,self.accounts[1].signer)
    @pytest.fixture
    def buyer_acc(self) -> tuple[str,str,AccountTransactionSigner]:
        addr, sk = self.accounts[2].address, self.accounts[2].private_key
        return (addr,sk,self.accounts[2].signer)

    def test_fund_box_algos(self,admin_acc:tuple[str,str,AccountTransactionSigner]):
        addr,sk,signer =  admin_acc
        sp = self.algod_client.suggested_params()
        app_client = client.ApplicationClient(self.algod_client,self.app,self.app_id,signer=signer)
        ptxn = TransactionWithSigner(
            txn = transaction.PaymentTxn(
                addr,sp,self.app_addr, int(1e5)
            ),
            signer = signer
        )

        r = app_client.call(
            Ecommerce.addFundBoxAlgoBalance,
            t= ptxn,
        )
        print(f"Admin deposited funds for boxes:{r.return_value}")
    def test_fund_box_algos_withdraw(self,admin_acc:tuple[str,str,AccountTransactionSigner]):
        addr,sk,signer =  admin_acc
        sp = self.algod_client.suggested_params()
        app_client = client.ApplicationClient(self.algod_client,self.app,self.app_id,signer=signer)

        r = app_client.call(
            Ecommerce.withdrawFundBoxAlgosBalance,
            a = int(1e4)
        )
        print(f"Admin withdraw funds for boxes:{r.return_value}")

    def test_buyer_pay_order_usdc(self,buyer_acc:tuple[str,str,AccountTransactionSigner]):
        addr,sk,signer =  buyer_acc
        sp = self.algod_client.suggested_params()
        app_client = client.ApplicationClient(self.algod_client,self.app,self.app_id,signer=signer)
        otxn = TransactionWithSigner(
            txn = transaction.PaymentTxn(
                addr,sp,self.app_addr, int(1e5)
            ),
            signer = signer
        )
        ptxn = TransactionWithSigner(
            txn = transaction.AssetTransferTxn(
                addr,sp,self.app_addr,1000,self.USDC
            ),
            signer = signer
        )
        r = app_client.call(
            Ecommerce.payOrder,
            oracle_pay=otxn,
            product_pay= ptxn,

        )
        print(f"Buyer pay order::{r.return_value}")



    def test_new_order(self,admin_acc:tuple[str,str,AccountTransactionSigner]):
        addr,sk,signer =  admin_acc
        app_client = client.ApplicationClient(self.algod_client,self.app,self.app_id,signer=signer)
        o = {
            "seller":"MSNHPFV3UYDPSSPVMJ7O3HX3CDXCIK2PUCTBB5GHBYAPLASK5TLEKP3PWI",
            "buyer": "RRXY3RSR2XRMJG3ZOBBTYXWLU6SKG3YJGUEEN4CC6MHOMCF4V2Q2ZYN4R4",
            "amount":int(1000),
            "token":self.USDC,
            "seller_state":1,
            "buyer_state":0
        }
        r = app_client.call(
            Ecommerce.newOrder,
            id="12313131313131231231312",
            order = o,
            boxes=[[app_client.app_id, "12313131313131231231312"]]
        )
        print(f"Admin places the order: {r.return_value}")

    def test_complete_order(self,admin_acc:tuple[str,str,AccountTransactionSigner]):
        addr,sk,signer =  admin_acc
        app_client = client.ApplicationClient(self.algod_client,self.app,self.app_id,signer=signer)
        o = {
            "seller":"MSNHPFV3UYDPSSPVMJ7O3HX3CDXCIK2PUCTBB5GHBYAPLASK5TLEKP3PWI",
            "buyer": "RRXY3RSR2XRMJG3ZOBBTYXWLU6SKG3YJGUEEN4CC6MHOMCF4V2Q2ZYN4R4",
            "amount":int(2e10),
            "token":self.USDC,
            "seller_state":1,
            "buyer_state":0
        }
        r = app_client.call(
            Ecommerce.completeOrder,
            id="2432423423542352",
            order = o,
            boxes=[[app_client.app_id, "2432423423542352"]]
        )
        print(f"Order Status: {r.return_value}")

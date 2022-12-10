from ast import Constant
import pytest
from algosdk.atomic_transaction_composer import *
from algosdk.future import transaction
from algosdk.v2client.algod import AlgodClient
from algosdk.encoding import decode_address
from beaker import client, sandbox
from beaker.client.application_client import ApplicationClient

from .contract import Ecommerce

class TestEcommerce:
    accounts = sandbox.get_accounts()
    algod_client:AlgodClient = sandbox.get_algod_client()
    app_addr = 'WKQ64D7YMYZUUUU7RHDCPSHZX7QM63TS2PZ32IM55Y4FEUIAYKHWFJRSLA'
    addr = accounts[0].address
    sk = accounts[0].private_key

    app = Ecommerce()
    app_client = client.ApplicationClient(algod_client,app,signer=AccountTransactionSigner(sk))

    license_id = 29
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

    def test_app_create(self):
        self.app,self.app_addr,_ = self.app_client.create()
        app_state = self.app_client.get_application_state()
        sender = self.app_client.get_sender()
        assert self.app_client.app_id > 0, "No app id created"
        print("Application Addr:")
        print(self.app_client.app_addr)
        print("========================================================")
        print("Application ID")
        print(self.app_client.app_id)
        print("========================================================")
    def test_setup(self):
        sp = self.algod_client.suggested_params()
        ptxn = TransactionWithSigner(
            txn = transaction.PaymentTxn(
                self.app_client.get_sender(), sp, self.app_client.app_addr,int(6e10)
            ),
            signer = self.app_client.get_signer(),
        )
        r = self.app_client.call(self.app.setup,t = ptxn)
        app_state = self.app_client.get_application_state()
        assert r.return_value == "setup_successfull", "Application must str message"

    def test_opt_token_usdc(self):
        sp = self.algod_client.suggested_params()
        ptxn = TransactionWithSigner(
            txn = transaction.PaymentTxn(
                self.app_client.get_sender(), sp, self.app_client.app_addr,int(1e7)
            ),
            signer = self.app_client.get_signer(),
        )
        r = self.app_client.call(self.app.addToken,a = 4)
        print("\n opt-in asset USDC")
        print(r.return_value)

    def test_balence_token_usdc(self):
        r = self.app_client.call(Ecommerce.readBalanceIndex,k = 1)
        print(r.return_value)

    def test_opt_token_usdt(self):
        sp = self.algod_client.suggested_params()
        ptxn = TransactionWithSigner(
            txn = transaction.PaymentTxn(
                self.app_client.get_sender(), sp, self.app_client.app_addr,int(1e7)
            ),
            signer = self.app_client.get_signer(),
        )
        r = self.app_client.call(self.app.addToken,a = 5)
        print("\n opt-in asset USDT")
        print(r.return_value)
    def test_seller_opt_in(self,seller_acc:tuple[str,str,AccountTransactionSigner]):
        addr,sk,signer =  seller_acc
        app_client = client.ApplicationClient(self.algod_client,self.app,self.app_client.app_id,signer=signer)
        r = app_client.opt_in()
        client_state = app_client.get_account_state()

    def test_buyer_opt_in(self,buyer_acc:tuple[str,str,AccountTransactionSigner]):
        addr,sk,signer =  buyer_acc
        app_client = client.ApplicationClient(self.algod_client,self.app,self.app_client.app_id,signer=signer)
        r = app_client.opt_in()

    def test_become_seller(self,seller_acc: tuple[str,str,AccountTransactionSigner]):
        addr,sk,signer =  seller_acc
        app_client = client.ApplicationClient(self.algod_client,self.app,self.app_client.app_id,signer=signer)
        sp = self.algod_client.suggested_params()

        otxn = TransactionWithSigner(
            txn = transaction.AssetTransferTxn(
                addr,sp,addr,int(0),self.license_id
            ),
            signer = signer
        )
        ptxn = TransactionWithSigner(
            txn = transaction.PaymentTxn(
                addr, sp, self.app_addr,int(4e4)
            ),
            signer = signer
        )
        r = app_client.call(self.app.payLicense,o=otxn,p = ptxn,a = self.license_id)
        app_state = app_client.get_account_state()
        assert r.return_value == "payment_license_successfull", "Application must return 1"

    # def test_become_seller(self,seller_acc: tuple[str,str,AccountTransactionSigner]):
    #     addr,sk,signer =  seller_acc
    #     app_client = client.ApplicationClient(self.algod_client,self.app,26,signer=signer)
    #     sp = self.algod_client.suggested_params()

    #     otxn = TransactionWithSigner(
    #         txn = transaction.AssetTransferTxn(
    #             addr,sp,addr,int(0),self.license_id
    #         ),
    #         signer = signer
    #     )
    #     ptxn = TransactionWithSigner(
    #         txn = transaction.PaymentTxn(
    #             addr, sp, 'WKQ64D7YMYZUUUU7RHDCPSHZX7QM63TS2PZ32IM55Y4FEUIAYKHWFJRSLA',int(4e4)
    #         ),
    #         signer = signer
    #     )
    #     r = app_client.call(self.app.payLicense,o=otxn,p = ptxn,a = self.license_id)
    #     app_state = app_client.get_account_state()
    #     assert r.return_value == "payment_license_successfull", "Application must return 1"

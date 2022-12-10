#!/usr/bin/env python3

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

    app_id = 26

    app = Ecommerce()


    def test_app_update(self):
        addr, sk = self.accounts[0].address, self.accounts[0].private_key
        signer = self.accounts[0].signer
        app_client = client.ApplicationClient(self.algod_client,self.app,self.app_id,signer=signer)
        sp = self.algod_client.suggested_params()

        r = app_client.update()
        app_state = app_client.get_account_state()

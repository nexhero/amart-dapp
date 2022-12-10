#!/usr/bin/env python3
import sys

from pyteal import abi

from beaker.client import ApplicationClient
from beaker.application import Application
from beaker.decorators import external
from beaker import sandbox
from smartcontract.contract import Ecommerce

def main(app_id):
    acct = sandbox.get_accounts().pop()
    algod_client  = sandbox.get_algod_client()

    app_client = ApplicationClient(
        client = algod_client,
        app = Ecommerce(),
        app_id=app_id,
        signer = acct.signer
    )

    app_client.update()

if __name__ == "__main__" :
    app_id = int(sys.argv[1])
    main(app_id)

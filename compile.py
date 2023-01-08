#!/usr/bin/env python3
import os
import sys

from algosdk.atomic_transaction_composer import *
from algosdk.future import transaction
from algosdk.v2client.algod import AlgodClient
from algosdk.encoding import decode_address
from beaker.client import ApplicationClient
from beaker.application import Application
from beaker.decorators import external
from beaker import sandbox
from smartcontract.contract import Ecommerce

def main():
    admin = sandbox.get_accounts()[0]

    algod_client  = sandbox.get_algod_client()

    app_client = ApplicationClient(
        client = algod_client,
        app = Ecommerce(),
        signer = admin.signer
    )

    Ecommerce().dump("artifacts")

    approval_program, _, approval_map = app_client.compile(
        app_client.app.approval_program, source_map=True
    )
    # print(approval_map.__dir__())
    print(approval_map.get_line_for_pc(2486))
    # print(approval_map.pc_to_line)


if __name__ == "__main__" :
    main()

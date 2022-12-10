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

def main(tokens):
    admin = sandbox.get_accounts()[0]
    seller = sandbox.get_accounts()[1]
    buyer = sandbox.get_accounts()[2]

    algod_client  = sandbox.get_algod_client()

    admin_client = ApplicationClient(
        client = algod_client,
        app = Ecommerce(),
        signer = admin.signer
    )
    seller_client = ApplicationClient(
        client = algod_client,
        app = Ecommerce(),
        signer = seller.signer
    )
    buyer_client = ApplicationClient(
        client = algod_client,
        app = Ecommerce(),
        signer = buyer.signer
    )


    app_id, app_addr, txid = admin_client.create()

    # Call Setup
    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn = transaction.PaymentTxn(
            admin_client.get_sender(), sp, admin_client.app_addr,int(6e10)
        ),
        signer = admin_client.get_signer(),
    )
    app_license = admin_client.call(Ecommerce.setup,t = ptxn)

    # Opt-in stable coins
    for i in range(1,len(tokens)):
        t = int(tokens[i])
        sp = algod_client.suggested_params()
        ptxn = TransactionWithSigner(
            txn = transaction.PaymentTxn(
                admin_client.get_sender(), sp, admin_client.app_addr,int(1e7)
            ),
            signer = admin_client.get_signer(),
        )
        admin_client.call(Ecommerce.addToken, a = t)

    print(f"app_id {app_id}")
    print(f"app_addr {app_addr}")
    print(f"app_license {app_license.return_value}")


if __name__ == "__main__" :
    tokens = sys.argv
    main(tokens)

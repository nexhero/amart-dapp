from .test_calls import admin_client, seller_client, buyer_client
import pytest

from algosdk.atomic_transaction_composer import *
from algosdk.future import transaction
from beaker import sandbox
from smartcontract.contract import Ecommerce

algod_client = sandbox.get_algod_client()


def test_seller_cancel_order(admin_client, seller_client, buyer_client, usdc) -> None:
    amount = int(1e10)
    order_id = "refund_6_usdc"
    # Buyer pay for the order
    sp = algod_client.suggested_params()
    otxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            buyer_client.get_sender(), sp, buyer_client.app_addr, int(1e10)
        ),
        signer=buyer_client.get_signer()
    )
    ptxn = TransactionWithSigner(
        transaction.AssetTransferTxn(
            buyer_client.get_sender(), sp, buyer_client.app_addr, amount, int(usdc)
        ),
        signer=buyer_client.get_signer()
    )
    r_payment = buyer_client.call(
        Ecommerce.payOrder,
        oracle_pay=otxn,
        product_pay=ptxn,
    )

    # Admin creates order in blockchain

    o = {
        "seller": seller_client.get_sender(),
        "buyer": buyer_client.get_sender(),
        "amount": amount,
        "token": int(usdc),
        "seller_state": 0,
        "buyer_state": 0
    }
    r_create_order = admin_client.call(
        Ecommerce.createOrder,
        k=order_id,
        order=o,
        boxes=[[admin_client.app_id, order_id]],
        foreign_assets=[admin_client.get_application_state()["oni"]]
    )

    # Seller Cancel order
    r_refund = seller_client.call(
        Ecommerce.sellerCancelOrder,
        k=order_id,
        accounts=[buyer_client.get_sender()],
        foreign_assets=[seller_client.get_application_state()["lni"]],
        boxes=[[admin_client.app_id, order_id]]
    )
    # Buyer withdraw tokens
    r_withdraw = buyer_client.call(
        Ecommerce.userWithdraw,
        t=int(usdc)
    )


    print("\n")
    print(f"Buyer Payment: {r_payment.return_value}")
    print(f"Admin creates order: {r_create_order.return_value}")
    print(f"Seller cancel order: {r_refund.return_value}")
    print(f"Buyer withdraw usdc: {r_withdraw.return_value}")


from .test_calls import admin_client, seller_client, buyer_client
import pytest

from algosdk.atomic_transaction_composer import *
from algosdk.future import transaction
from beaker import sandbox
from smartcontract.contract import Ecommerce

algod_client = sandbox.get_algod_client()


def test_process_usdc_order(admin_client, seller_client, buyer_client, usdc) -> None:
    amount = int(1e10)
    order_id = "order_3_usdc"
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
        foreign_assets=[admin_client.get_application_state()["oni"]],
        boxes=[[admin_client.app_id, order_id]]
    )

    # Seller accepts

    r_seller_accept = seller_client.call(
        Ecommerce.sellerAcceptOrder,
        k=order_id,
        foreign_assets=[(seller_client.get_application_state()["lni"])],
        boxes=[[seller_client.app_id, order_id]]
    )
    # Buyer payout tokens to seller
    r_payout = buyer_client.call(
        Ecommerce.buyerCompleteOrder,
        k=order_id,
        accounts=[seller_client.get_sender()],
        boxes=[[buyer_client.app_id, order_id]]
    )

    # Seller withdraw tokens
    r_seller_withdraw = seller_client.call(
        Ecommerce.userWithdraw,
        t=int(usdc)
    )

    assert int(r_seller_withdraw.return_value) == 0, "The balance must be zero"
    print("\n")
    print(f"Buyer Payment: {r_payment.return_value}")
    print(f"Admin creates order: {r_create_order.return_value}")
    print(f"Seller accept order: {r_seller_accept.return_value}")
    print(f"Buyer payout order: {r_payout.return_value}")
    print(f"Seller Withdraw: {r_seller_withdraw.return_value}")

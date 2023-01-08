from algosdk.abi import ABIType
from pyteal import abi, TealType, Int, Seq

from beaker import (
    Application,
    ReservedAccountStateValue,
    opt_in,
    external,
    sandbox,
    client,
    identity_key_gen,
)
from algosdk.abi import ABIType
from algosdk.encoding import encode_address, decode_address
from algosdk.atomic_transaction_composer import TransactionWithSigner
from algosdk.future.transaction import *
from beaker.client import ApplicationClient
from pyteal import *
from beaker import *
from smartcontract.contract import Ecommerce



def print_boxes(app_client: client.ApplicationClient):
    order_codec = ABIType.from_string(str(Ecommerce.Order().type_spec()))

    # contents = app_client.get_box_contents(b'order_1')
    # order_record = order_codec.decode(contents)
    # print(f"{order_record} ")

    boxes = app_client.get_box_names()
    print(f"{len(boxes)} boxes found")
    for box_name in boxes:
        contents = app_client.get_box_contents(box_name)
        order_record = order_codec.decode(contents)
        print(f"\t{box_name} => {order_record} ")


def main():
    admin = sandbox.get_accounts()[0]
    algod_client  = sandbox.get_algod_client()

    admin_client = ApplicationClient(
        client = algod_client,
        app = Ecommerce(),
        app_id = 11,
        signer = admin.signer
    )
    print_boxes(admin_client)

if __name__=='__main__':
    main()

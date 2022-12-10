from pyteal import *
from typing import Final
from beaker import (
    Application,
    update,
    create,
    opt_in,
    AccountStateValue,
    ReservedAccountStateValue,
    ApplicationStateValue,
    ReservedApplicationStateValue,
    Authorize,
    external,
    internal,
    client,
    consts,
)
from beaker.lib.storage import Mapping, MapElement
class Ecommerce(Application):

    """
    This smartcontract works as escrow between buyer and sellers, is the main point entrace to make request
    to the oracle."""

    _oracle_fees = 1000         # Default oracle fees
    _commission_fees = 1        # Default commission
    _seller_cost = 4000         # Default price for buying a license

    # TODO: Add id for stbl coint v2 algofi and algo

    __USDC = 4                  # Asset ID for USDC
    __USDT = 5                  # Asset ID for USDT
    __STBL = 10                 # TODO: Create the stable coin in the sandbox
    # Define constans variables for the balance structure
    __MAX_DEPOSIT_TOKENS = 6    # The smart contract will support only 7 different tokens
    __ALGO_I = 0                # Index algo tokens for deposit
    __USDC_I = 1                # Index usdc tokens for deposit
    __USDT_I = 2                # Index usdt tokens for deposit
    __STBL_2_I = 3             # Index stable coin (algofi protocol) for deposit

    # Define constans variables for the order structure
    ORDER_POSTED = 0            # Buyer made an order
    ORDER_PENDING = 1           # Seller order initial state
    ORDER_ACCEPTED = 2          # Buyer/Seller accepted the order
    ORDER_CANCELED = 3          # Buyer/Seller Canceled the order
    ORDER_REJECTED = 4          # Seller Rejected the order

    ###########################################
    # DEFINE STRUCTURES FOR THE SMARTCONTRACT #
    ###########################################

    class Order(abi.NamedTuple):
        """
        Define the order structure, this store the current bussines for the buyer.
        For each order, buyer creates a box and only seller, buyer and the admin can modify the box
        """

        seller: abi.Field[abi.Address]     # The seller address
        buyer: abi.Field[abi.Address]      # The buyer address
        amount: abi.Field[abi.Uint64]      # the total tokens deposited by the buyer
        token: abi.Field[abi.Uint64]       # The assete id used for the transactions
        #----- Each address update the state of the order -------
        seller_state: abi.Field[abi.Uint8] # State order set by the seller [1=PENDING,2=ACCEPTED,3=CANCELED,4=CANCELED]
        buyer_state: abi.Field[abi.Uint8]  # State order set by the buyer [0=POSTED,2=ACCEPTED,3=CANCELED]


    #################################################
    # DEFINE ALL GLOBAL STATE FOR THE SMARTCONTRACT #
    #################################################
    oracle_address: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        key=Bytes("o"),
        default=Global.creator_address(),
        descr="The oracle address that receive all the request."
    )

    commission_fees: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("cf"),
        default=Int(_commission_fees),
        descr="Store the fees that seller pay for selling products"
    )

    oracle_fees: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("of"),
        default = Int(_oracle_fees),
        descr="Define the oracle fees that user pay for making requests."
    )
    license_id: Final[ApplicationStateValue] = ApplicationStateValue(
        #The NFT id that represent the license
        stack_type = TealType.uint64,
        key=Bytes("lid"),
        default = Int(0),
        descr="The NFT that represents an user as seller."
    )
    license_cost: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("lc"),
        default = Int(_seller_cost),
        descr="If an user become a seller, it must pay some algos, the amount of algo deposited is used to insurance the seller,"
    )
    earning: Final[ReservedApplicationStateValue] = ReservedApplicationStateValue(
        stack_type = TealType.uint64,
        max_keys = __MAX_DEPOSIT_TOKENS,
        descr = "Manage the earning by the smartcontract"
    )
    box_algos_balance: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("bab"),
        default=Int(0),
        descr="Current algos available to create boxes in the smartcontract, the smartcontract pay a percentange for the cost of creating a box"
    )
    box_pay_percent: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("bpp"),
        default=Int(50),         # The smartcontract cover for the 50%
        descr="The percentage that smartcontract cover for creating boxes; default 50% it will ~0.25 algos"
    )
    # Box mapping to store orders
    order_records = Mapping(abi.Byte, Order)

    ################################################
    # DEFINE ALL LOCAL STATE FOR THE SMARTCONTRACT #
    ################################################



    ###################
    # UTILS FUNCTIONS #
    ###################
    @internal(TealType.uint64)
    def getBalanceAssetIndex(self, a):
        return Cond(
            [a == Int(0), Return(Int(self.__ALGO_I))],
            [a == Int(self.__USDC), Return(Int(self.__USDC_I))],
            [a == Int(self.__USDT), Return(Int(self.__USDT_I))],
            [a == Int(self.__STBL), Return(Int(self.__STBL_2_I))]
        )
    ############################
    # admin external functions #
    ############################

    @create
    def create(self):
        """On deploy application."""
        return Seq(
            self.initialize_application_state(),
        )

    @update
    def update(self):
        return Approve()

    @opt_in
    def opt_in(self):
        """Account registered into the smartcontract"""
        return Seq(
            self.initialize_account_state(),
            # self.acct_state.initialize(),

        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def addToken(self,
                 a: abi.Asset,
                 *, output:abi.Uint64):
        """Enable new tokens for payment"""
        return Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: a.asset_id(),
                    TxnField.asset_amount: Int(0),
                    TxnField.asset_receiver: self.address,
                }
            ),
            InnerTxnBuilder.Submit(),
            output.set(self.getBalanceAssetIndex(a.asset_id()))
        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def setup(self,
              t: abi.PaymentTransaction,
              *,output:abi.String):
        """
        The application receive some algos, and create the seller license nft
        """
        return Seq(
            Assert(
                t.get().receiver() == Global.current_application_address()
            ),
            # Create the Nft
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_total: Int(100000000),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_unit_name: Bytes("asl"),
                TxnField.config_asset_name: Bytes("aMart Seller Lincense"),
                TxnField.config_asset_url: Bytes("https://amart.com"),
                TxnField.config_asset_manager: Global.current_application_address(),
                TxnField.config_asset_reserve: Global.current_application_address(),
                TxnField.config_asset_freeze: Global.current_application_address(),
                TxnField.config_asset_clawback: Global.current_application_address(),

            }),
            InnerTxnBuilder.Submit(),
            self.license_id.set(InnerTxn.created_asset_id()),
            output.set("setup_successfull")
        )
    @external(authorize=Authorize.only(Global.creator_address()))
    def addFundBoxAlgoBalance(
            self,
            t: abi.PaymentTransaction,
            *,output:abi.Uint64
    ):
        #add Funds for creating boxes
        return Seq(
            Assert(
                t.get().receiver() == Global.current_application_address()
            ),
            self.box_algos_balance.increment(t.get().amount()),
            output.set(self.box_algos_balance)
        )
    @external(authorize=Authorize.only(Global.creator_address()))
    def withdrawFundBoxAlgosBalance(
            self,
            a: abi.Uint64,
            *,output:abi.Uint64
    ):
        return Seq(
            Assert(
                a.get() <= self.box_algos_balance
            ),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: Txn.sender(),
                TxnField.amount: a.get(),
            }),
            InnerTxnBuilder.Submit(),
            self.box_algos_balance.decrement(a.get()),
            output.set(self.box_algos_balance)
        )
    @external(read_only=True, authorize=Authorize.only(Global.creator_address()))
    def readBalanceIndex(self,
                         k: abi.Uint8,
                         *, output: abi.Byte):
        # Read the earning that the smartcontract made
        return output.set(self.earning[k])

    @external(authorize=Authorize.only(Global.creator_address()))
    def newOrder(
            self,
            id: abi.String,
            order: Order,
            *,output: abi.String):
        order_id = ScratchVar(TealType.bytes) # I need to convert the id string into bytes
        order_exist = ScratchVar(TealType.uint64) # Flag check if the box already exist

        return Seq(
            order_id.store(id.get()),
            order_exist.store(MapElement(order_id.load(),self.Order).exists()),

            # Check if the box was already created
            If(order_exist.load())
            .Then(
                output.set("order_alredy_exist"),
            )
            .Else(
                self.order_records[order_id.load()].set(order),
                output.set("new_order_created")

            )

        )
    @external(authorize=Authorize.only(Global.creator_address()))
    def completeOrder(
            self,
            id: abi.String,
            order: Order,
            *, output: abi.Uint64
    ):
        order_id = ScratchVar(TealType.bytes)
        o = abi.make(abi.Uint64)
        return Seq(
            order_id.store(id.get()),
            o.set(MapElement(order_id.load(), self.Order).exists()),
            output.set(o)
        )
    ##################
    # USER FUNCTIONS #
    ##################

    @external
    def payLicense(self,
                   o: abi.AssetTransferTransaction,
                   p: abi.PaymentTransaction, # The user pay with algos
                   a: abi.Asset,
                   *,output: abi.String):
        # User pay with algos to become a seller in the platform
        return Seq(
            Assert(
                And(
                    p.get().amount() >= self.license_cost,
                    o.get().xfer_asset() == self.license_id,
                    a.asset_id() == self.license_id
                )

            ),
            InnerTxnBuilder.Begin(),

            # Transfer the nft to the seller address
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.asset_receiver: Txn.sender(),
                TxnField.asset_amount: Int(1),
                TxnField.xfer_asset: self.license_id,
            }),
            InnerTxnBuilder.Next(),
            # Freeze the nft into the seller address
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetFreeze,
                TxnField.freeze_asset: self.license_id,
                TxnField.freeze_asset_account: Txn.sender(),
                TxnField.freeze_asset_frozen: Int(1)
            }),
            InnerTxnBuilder.Submit(),
            output.set("payment_license_successfull")
        )

    @external
    def payOrder(self,
                 oracle_pay: abi.PaymentTransaction,
                 product_pay: abi.AssetTransferTransaction,
                 *, output: abi.String):
        # A buyer send the payment to the smartcontract, the private oracle will validate the payment

        return Seq(
            # Validate input data
            Assert(
                oracle_pay.get().amount() >= self.oracle_fees,
                oracle_pay.get().receiver() == Global.current_application_address(),
                product_pay.get().asset_receiver() == Global.current_application_address(),

                Or(
                    product_pay.get().xfer_asset() == Int(self.__USDC),
                    product_pay.get().xfer_asset() == Int(self.__USDT),
                    product_pay.get().xfer_asset() == Int(self.__STBL),
                ),
                product_pay.get().asset_amount() >= Int(0),
            ),
            output.set("payment_successfull")
        )

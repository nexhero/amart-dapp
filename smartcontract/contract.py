from pyteal import *
from typing import Final
from beaker import (
    Application,
    update,
    create,
    opt_in,
    ReservedAccountStateValue,
    ApplicationStateValue,
    ReservedApplicationStateValue,
    Authorize,
    external,
    internal,
)
from .dappmessages import EcommerceMessage
from beaker.lib.storage import Mapping, MapElement


class Ecommerce(Application):

    """
    This smart contract works as escrow between buyer and sellers, is the main point entrance to make request
    to the oracle."""

    ################################################
    # Define Default Values for the smart contract #
    ################################################

    __REQUEST_FEES = 1000       # Default fees for making request to the observer application.
    __COMMISSION_FEES = 135     # Default commission
    __LICENSE_COST = 4000       # Default price for buying a license

    ##########################################
    # Assets that smart contract will manage #
    ##########################################
    __USDC = 1                  # Asset ID for USDC
    __USDT = 2                  # Asset ID for USDT
    __STBL2 = 10                # TODO: Create the stable coin in the sandbox

    #######################################################
    # Define constant variables for the balance structure #
    #######################################################
    __MAX_DEPOSIT_TOKENS = 6    # The smart contract will support only 7 different tokens
    __ALGO_I = 0                # Index algo tokens for deposit
    __USDC_I = 1                # Index usdc tokens for deposit
    __USDT_I = 2                # Index usdt tokens for deposit
    __STBL2_I = 3              # Index stable coin (algofi protocol) for deposit

    #####################################################
    # Define constant variables for the order structure #
    #####################################################
    ORDER_BUYER_POSTED = 0
    ORDER_BUYER_CANCEL = 1

    ORDER_SELLER_PENDING = 0
    ORDER_SELLER_ACCEPTED = 1

    ###########################################
    # DEFINE STRUCTURES FOR THE SMARTCONTRACT #
    ###########################################
    class Order(abi.NamedTuple):
        """
            Define the order structure, this store the current business for the buyer.
            For each order, buyer creates a box and only seller, buyer and the admin can modify the box
            """
        seller: abi.Field[abi.Address]     # The seller address
        buyer: abi.Field[abi.Address]      # The buyer address
        amount: abi.Field[abi.Uint64]      # the total tokens deposited by the buyer
        token: abi.Field[abi.Uint64]       # The asset id used for the transactions
        seller_state: abi.Field[abi.Uint8]  # State order set by the seller [1=PENDING,2=ACCEPTED,3=CANCELED,4=CANCELED]
        buyer_state: abi.Field[abi.Uint8]  # State order set by the buyer [0=POSTED,2=ACCEPTED,3=CANCELED]


    #################################################
    # DEFINE ALL GLOBAL STATE FOR THE SMARTCONTRACT #
    #################################################

    """ # Global Variables """
    earning: Final[ReservedApplicationStateValue] = ReservedApplicationStateValue(
        stack_type=TealType.uint64,
        max_keys=__MAX_DEPOSIT_TOKENS,
        descr="Collect earning that smart contract made"
    )
    """Collect the earning that smart contract made."""

    commission_fees: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("cf"),
        default=Int(__COMMISSION_FEES),
        descr="Fees charged for product."
    )
    """Store the fees that users pay for the products"""

    request_fees: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("rf"),
        default=Int(__REQUEST_FEES),
        descr="Define the oracle fees that user pay for making requests."
    )
    """The cost for making request to the observer application"""

    license_nft_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("lni"),
        default=Int(0),
        descr="The NFT that represents an user as seller."
    )
    """License nft created by the smart contract, that represent a seller."""

    license_price: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("lp"),
        default=Int(__LICENSE_COST),
        descr="NFT ID that represent a seller address"
    )
    """Store the price for becoming a seller."""

    observer_nft_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("oni"),
        default=Int(0),
        descr="NFT for observer accounts"
    )
    """Nft that represent address that can process order in the smart contract."""

    active_box_orders: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("abo"),
        default=Int(0),
        descr="Count the active orders"
    )
    """Store how many boxes are active"""

    maintance: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("m"),
        default=Int(0),
        descr="Flag to know if the application is maintance mode "
    )
    """Flag to turn/off mantinance"""

    auto_process_delay: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("apd"),
        default=Int(100),       # TODO: Create a const for default value
        descr="How many days wait before to auto-process the application"
    )
    """Store how many days wait before to auto-process order in case one of the user didn't respond"""

    # TODO:Remove this variable
    debug: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        key=Bytes("debug_b"),
    )

    # Local Variables
    user_balance: Final[ReservedAccountStateValue] = ReservedAccountStateValue(
        stack_type=TealType.uint64,
        max_keys=__MAX_DEPOSIT_TOKENS,
        descr="Store refunds tokens."
    )

    order_records = Mapping(abi.Byte, Order)
    """Represent the active ordes in the smart contract."""

    ################################################
    # DEFINE ALL LOCAL STATE FOR THE SMARTCONTRACT #
    ################################################

    ###################
    # UTILS FUNCTIONS #
    ###################

    @internal(TealType.uint64)
    def getAssetIndex(self, a: abi.Uint64):
        """Get the index in earning for the specific asset id"""
        return Cond(
            [a.get() == Int(0), Return(Int(self.__ALGO_I))],
            [a.get() == Int(self.__USDC), Return(Int(self.__USDC_I))],
            [a.get() == Int(self.__USDT), Return(Int(self.__USDT_I))],
            [a.get() == Int(self.__STBL2), Return(Int(self.__STBL2_I))]
        )

    @internal(TealType.uint64)
    def incrementUserBalance(self, addr: abi.Address, amount: abi.Uint64, token: abi.Uint64):
        """Increment the temp balance for a buyer addr"""
        current_balance = abi.make(abi.Uint64)
        k = abi.make(abi.Uint8)

        return Seq(

            k.set(self.getAssetIndex(token)),
            current_balance.set(self.user_balance[k][addr.get()]),
            self.user_balance[k][addr.get()].set(current_balance.get()+amount.get()),
            Return(self.user_balance[k][addr.get()])

        )

    @internal(TealType.uint64)
    def incrementBalanceAssetIndex(self, amount: abi.Uint64, token: abi.Uint64):
        """Increment the earning's balance for a token"""
        current_balance = abi.make(abi.Uint64)
        k = abi.make(abi.Uint8)
        return Seq(
            k.set(self.getAssetIndex(token)),
            current_balance.set(self.earning[k]),
            self.earning[k].set(current_balance.get()+amount.get()),
            Return(self.earning[k])
        )

    @internal(TealType.uint64)
    def decrementUserBalance(self, addr: abi.Address, amount: abi.Uint64, token: abi.Uint64):
        """Decrement the user balance for a token"""
        current_balance = abi.make(abi.Uint64)
        new_balance = abi.make(abi.Uint64)
        k = abi.make(abi.Uint8)
        return Seq(
            k.set(self.getAssetIndex(token)),
            Assert(amount.get() <= self.user_balance[k][addr.get()]),
            current_balance.set(self.user_balance[k][addr.get()]),
            new_balance.set(current_balance.get() - amount.get()),
            self.user_balance[k][addr.get()].set(new_balance.get()),
            Return(self.user_balance[k][addr.get()])
        )
    @internal(TealType.uint64)
    def decrementBalanceAssetIndex(self, amount: abi.Uint64, token: abi.Uint64):
        """Decrement the earning's balance for a token"""
        current_balance = abi.make(abi.Uint64)
        k = abi.make(abi.Uint8)
        return Seq(
            k.set(self.getAssetIndex(token)),
            Assert(amount.get() <= self.earning[k], comment=EcommerceMessage.ERROR_NO_FUNDS),
            current_balance.set(self.earning[k]),
            current_balance.set(current_balance.get() - amount.get()),
            self.earning[k].set(current_balance.get()),
            Return(self.earning[k])
        )

    @internal(TealType.uint64)
    def isObserver(self):
        """Check if the sender is an observer"""
        r = AssetHolding.balance(Txn.sender(), self.observer_nft_id)
        return Seq(
            r,                  # Get the balance for the observer nft
            If(r.value() > Int(0))
            .Then(
                Return(Int(1))
            )
            .Else(
                Return(Int(0))
            )
        )
    @internal(TealType.uint64)
    def isAdmin(self):
        """Check if the sender is administrator"""
        return Seq(
            # Probably manage the admin address in a global variable
            If(Txn.sender() == Global.creator_address())
            .Then(
                Return(Int(1))
            )
            .Else(
                Return(Int(0))
            )
        )
    @internal(TealType.uint64)
    def isSeller(self):
        """Check if the address is a seller account."""
        r = AssetHolding.balance(Txn.sender(), self.license_nft_id)
        return Seq(
            r,
            If(r.value() > Int(0))
            .Then(
                Return(Int(1))
            )
            .Else(
                Return(Int(0))
            )
        )
    @internal(TealType.none)
    def countOrderIncrement(self):
        """Increment the count active orders"""
        return Seq(
            self.active_box_orders.increment(Int(1))
        )
    @internal(TealType.none)
    def countOrderDecrement(self):
        """Decrement the count active orders"""
        return Seq(
            self.active_box_orders.decrement(Int(1))
        )
    @internal(TealType.uint64)
    def orderExists(self, k: abi.String):
        """Check if the box for a specific order id exists"""
        return MapElement(k.get(), self.Order).exists()

    @internal(TealType.none)
    def createBoxOrder(self, k: abi.String, data: Order):
        """Try to create an order, if the order key already exist exit program"""
        return Seq(
            Assert(self.orderExists(k) == Int(0), comment=EcommerceMessage.ERROR_ORDER_EXIST),
            self.order_records[k.get()].set(data),
            self.countOrderIncrement(),
        )
    @internal(TealType.none)
    def deleteBoxOrder(self, k: abi.String):
        """Delete an order box using box key"""
        r = abi.make(abi.Uint64)
        return Seq(
            # TODO: Apply logic to send tokens to the seller and increment the earning balance for the smartcontract
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            r.set(self.order_records[k.get()].delete()),
            self.countOrderDecrement(),
        )
    @internal(TealType.uint64)
    def addrIsBuyerInOrder(self, k: abi.String):
        """Check if the sender is the buyer for a specific order"""
        addr = abi.make(abi.Address)
        return Seq(
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            (o := Ecommerce.Order()).decode(self.order_records[k.get()].get()),
            o.buyer.store_into(addr),
            If(addr.get() == Txn.sender())
            .Then(
                Return(Int(1))
            )
            .Else(
                Return(Int(0))
            )
        )
    @internal(TealType.uint64)
    def addrIsSellerInOrder(self, k: abi.String):
        """Check if the sender is the seller for a specific order"""

        addr = abi.make(abi.Address)
        return Seq(
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            (o := Ecommerce.Order()).decode(self.order_records[k.get()].get()),
            o.seller.store_into(addr),
            If(addr.get() == Txn.sender())
            .Then(
                Return(Int(1))
            )
            .Else(
                Return(Int(0))
            )
        )
    @internal(TealType.uint64)
    def getOrderSellerState(self, k: abi.String):
        """Get the current seller's state for the order."""
        state = abi.make(abi.Uint8)
        return Seq(
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            (o := Ecommerce.Order()).decode(self.order_records[k.get()].get()),
            o.seller_state.store_into(state),
            Return(state.get())
        )

    @internal(TealType.none)
    def sendStblCoinTo(self,
                       _to,
                       amount,
                       token,
                       msg):
        """Send any of the stable coind holded by the smart contract"""
        # TODO: return the transaction id
        return Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.asset_receiver: _to,
                TxnField.asset_amount: amount,
                TxnField.xfer_asset: token,
                TxnField.note: msg,
            }),
            InnerTxnBuilder.Submit()
        )
    @internal(TealType.none)
    def updateSellerOrderState(self, k: abi.String, value: abi.Uint8):
        """Seller update state"""
        seller = abi.make(abi.Address)
        buyer = abi.make(abi.Address)
        amount = abi.make(abi.Uint64)
        token = abi.make(abi.Uint64)
        buyer_state = abi.make(abi.Uint8)
        return Seq(
            (order := Ecommerce.Order()).decode(self.order_records[k.get()].get()),

            order.seller.store_into(seller),
            order.buyer.store_into(buyer),
            order.amount.store_into(amount),
            order.token.store_into(token),
            order.buyer_state.store_into(buyer_state),

            (updated_order := Ecommerce.Order()).set(
                seller,
                buyer,
                amount,
                token,
                value,
                buyer_state,
            ),
            self.order_records[k.get()].set(updated_order),
        )

    @internal(TealType.none)
    def updateBuyerOrderState(self, k: abi.String, value: abi.Uint8):
        """Buyer update state"""
        seller = abi.make(abi.Address)
        buyer = abi.make(abi.Address)
        amount = abi.make(abi.Uint64)
        token = abi.make(abi.Uint64)
        seller_state = abi.make(abi.Uint8)
        return Seq(
            (order := Ecommerce.Order()).decode(self.order_records[k.get()].get()),

            order.seller.store_into(seller),
            order.buyer.store_into(buyer),
            order.amount.store_into(amount),
            order.token.store_into(token),
            order.seller_state.store_into(seller_state),

            (updated_order := Ecommerce.Order()).set(
                seller,
                buyer,
                amount,
                token,
                seller_state,
                value,
            ),
            self.order_records[k.get()].set(updated_order),
        )

    @internal(TealType.uint64)
    def calcCommission(self, v: abi.Uint64):
        r = ScratchVar(TealType.uint64)

        return Seq(
            r.store((v.get() / Int(10000)) * self.commission_fees),
            Return(r.load())
        )

    @internal(TealType.none)
    def payoutSeller(self, k: abi.String):
        """Payout to the seller"""
        t = abi.make(abi.Uint64)
        amount = abi.make(abi.Uint64)
        commission = abi.make(abi.Uint64)
        deposit = abi.make(abi.Uint64)
        addr = abi.make(abi.Address)
        r = abi.make(abi.Uint64)  # the increment function has a return value
        earning = abi.make(abi.Uint64)  # Junk variable
        return Seq(
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            (o := Ecommerce.Order()).decode(self.order_records[k.get()].get()),
            o.token.store_into(t),
            o.amount.store_into(amount),
            o.seller.store_into(addr),
            commission.set(self.calcCommission(amount)),
            deposit.set(amount.get()-commission.get()),
            r.set(self.incrementUserBalance(addr, deposit, t)),
            earning.set(self.incrementBalanceAssetIndex(commission, t)),
            self.deleteBoxOrder(k)

        )
    @internal(TealType.none)
    def refundBuyer(self, k: abi.String):
        """Refund token to the buyer user"""
        t = abi.make(abi.Uint64)
        amount = abi.make(abi.Uint64)
        addr = abi.make(abi.Address)
        r = abi.make(abi.Uint64)  # the increment function has a return value
        return Seq(
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            (o := Ecommerce.Order()).decode(self.order_records[k.get()].get()),
            o.token.store_into(t),
            o.amount.store_into(amount),
            o.buyer.store_into(addr),
            r.set(self.incrementUserBalance(addr, amount, t)),
            self.deleteBoxOrder(k)
        )

    #######################
    # END UTILS FUNCTIONS #
    #######################

    #####################
    # DEFAULT FUNCTIONS #
    #####################
    @create
    def create(self):
        """On deploy application."""
        return Seq(
            self.initialize_application_state(),
        )
    @update
    def update(self):
        """Update the application"""
        return Approve()

    @opt_in
    def opt_in(self):
        """Account registered into the smartcontract"""
        return Seq(
            # TODO: Set user_balance to zero
            self.initialize_account_state(),
        )

    ###################
    # ADMIN FUNCTIONS #
    ###################
    @external(authorize=Authorize.only(Global.creator_address()))
    def addFundsEarning(self,
                        att: abi.AssetTransferTransaction,
                        token: abi.Asset,
                        *, output: abi.Uint64):
        """Administrator add funds to the earning balance."""
        token_id = abi.make(abi.Uint64)
        amount = abi.make(abi.Uint64)
        balance = abi.make(abi.Uint64)
        return Seq(
            token_id.set(token.asset_id()),
            amount.set(att.get().asset_amount()),
            balance.set(self.incrementBalanceAssetIndex(amount, token_id)),
            Assert(
                cond=att.get().asset_receiver() == Global.current_application_address(),
                comment=EcommerceMessage.ERROR_RECEIVER_NOT_APP_ADDR
            ),

            output.set(balance.get())

        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def withdrawEarnings(self,
                         amount: abi.Uint64,
                         token: abi.Asset,
                         *, output: abi.Uint64):
        """Administrator withdraw the earning to the creator"""
        token_id = abi.make(abi.Uint64)
        balance = abi.make(abi.Uint64)
        return Seq(
            token_id.set(token.asset_id()),
            balance.set(self.decrementBalanceAssetIndex(amount, token_id)),
            self.sendStblCoinTo(
                Global.creator_address(),
                amount.get(),
                token_id.get(),
                Bytes("Withdraw earning")
            ),
            output.set(balance.get())
        )


    @external(authorize=Authorize.only(Global.creator_address()))
    def setup(self,
              t: abi.PaymentTransaction,
              *, output: abi.Uint64):
        """
        The application receive some algos, and create the seller license nft.
        >**TODO:** Probably is better if the license for the seller is manage in another application
        """
        return Seq(
            Assert(
                t.get().receiver() == Global.current_application_address()
            ),

            # Transaction to create license nft
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
            # Transaction to create observer nft
            InnerTxnBuilder.Next(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_total: Int(100000000),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_unit_name: Bytes("aop"),
                TxnField.config_asset_name: Bytes("aMart Observer Pass"),
                TxnField.config_asset_url: Bytes("https://amart.com"),
                TxnField.config_asset_manager: Global.current_application_address(),
                TxnField.config_asset_reserve: Global.current_application_address(),
                TxnField.config_asset_freeze: Global.current_application_address(),
                TxnField.config_asset_clawback: Global.current_application_address(),
            }),
            InnerTxnBuilder.Submit(),
            self.license_nft_id.set(Gitxn[0].created_asset_id()),  # Store the asset id created for license
            self.observer_nft_id.set(Gitxn[1].created_asset_id()),  # Store the asset id created for observer
            output.set(self.license_nft_id)
        )
    @external(authorize=Authorize.only(Global.creator_address()))
    def addToken(self,
                 a: abi.Asset,
                 *, output: abi.Uint64):
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
            output.set(Int(1))
        )
    @external
    def createOrder(self,
                    k: abi.String,
                    order: Order,
                    *, output: abi.String):
        """An observer watch for a payment transaction, validate and create the order"""
        return Seq(
            Assert(             # Only the creator or an observer can use this method
                Or(
                    self.isAdmin(),
                    self.isObserver(),
                ),
                comment=EcommerceMessage.ERROR_INVALID_CREDENTIALS
            ),
            self.createBoxOrder(k, order),
            output.set(EcommerceMessage.Ok_ORDER_CREATED)
        )
    @external
    def adminRefundBuyer(self,
                         k: abi.String,
                         *, output: abi.String):
        """ Administrator refund token to buyer address"""
        return Seq(
            Assert(             # -- Only a validated address can call this method
                Or(
                    self.isAdmin(),
                    self.isObserver(),
                ),
                comment=EcommerceMessage.ERROR_INVALID_CREDENTIALS,
            ),
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            self.refundBuyer(k),
            output.set(EcommerceMessage.OK_PAYMENT_SUCCESSFULL)
        )
    @external
    def adminPayoutSeller(self,
                          k: abi.String,
                          *, output: abi.String):
        """ Administrator payout to the seller account."""
        return Seq(
          Assert(
            Or(
              self.isAdmin(),
              self.isObserver()
            ),
            comment=EcommerceMessage.ERROR_INVALID_CREDENTIALS,
          ),
          self.payoutSeller(k),
          output.set(EcommerceMessage.OK_PAYOUT_SELLER)
        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def setCommisionFees(self,
                         v: abi.Uint64,
                         *, output: abi.Uint64):
        """Administrator update the commission value"""
        return Seq(
            self.commission_fees.set(v.get()),
            output.set(self.commission_fees)
        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def setLicensePrice(self,
                        v: abi.Uint64,
                        *, output: abi.Uint64):
        """Administrator update the price for nft"""
        return Seq(
            self.license_price.set(v.get()),
            output.set(self.license_price)
        )

    @external(authorize=Authorize.only(Global.creator_address()))
    def setObserverFees(self,
                        v: abi.Uint64,
                        *, output: abi.Uint64):
        """Administrator update the fees that user paid for making request """
        return Seq(
            self.request_fees.set(v.get()),
            output.set(self.request_fees)
        )

    #######################
    # END ADMIN FUNCTIONS #
    #######################
    @external
    def payLicense(self,
                   p: abi.PaymentTransaction,  # The user pay with algos
                   a: abi.Asset,
                   *, output: abi.String):
        """User pay with algos to become a seller in the platform"""
        return Seq(
            Assert(
                p.get().amount() >= self.license_price,
                comment=EcommerceMessage.ERROR_AMOUNT
            ),
            Assert(
                a.asset_id() == self.license_nft_id,
                comment=EcommerceMessage.ERROR_INVALID_TOKEN,
            ),
            Assert(
                self.isSeller() == Int(0),
                comment=EcommerceMessage.ERROR_USER_IS_SELLER
            ),

            InnerTxnBuilder.Begin(),

            # Transfer the nft to the seller address
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.asset_receiver: Txn.sender(),
                TxnField.asset_amount: Int(1),
                TxnField.xfer_asset: self.license_nft_id,
            }),
            InnerTxnBuilder.Next(),
            # Freeze the nft into the seller address
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetFreeze,
                TxnField.freeze_asset: self.license_nft_id,
                TxnField.freeze_asset_account: Txn.sender(),
                TxnField.freeze_asset_frozen: Int(1)
            }),
            InnerTxnBuilder.Submit(),
            output.set(EcommerceMessage.OK_PAYMENT_SUCCESSFULL)
        )

    @external
    def payOrder(self,
                 oracle_pay: abi.PaymentTransaction,
                 product_pay: abi.AssetTransferTransaction,
                 *, output: abi.String):
        """A buyer sends the payment to the smart contract, the private oracle will validate the payment"""
        amount = abi.make(abi.Uint64)
        token = abi.make(abi.Uint64)
        return Seq(
            # Validate input data
            amount.set(product_pay.get().asset_amount()),
            token.set(product_pay.get().xfer_asset()),

            Assert(
                oracle_pay.get().amount() >= self.request_fees,
                comment=EcommerceMessage.ERROR_WRONG_AMOUNT_FEES
            ),
            Assert(
                oracle_pay.get().receiver() == Global.current_application_address(),
                comment=EcommerceMessage.ERROR_RECEIVER_NOT_APP_ADDR
            ),
            Assert(
                product_pay.get().asset_receiver() == Global.current_application_address(),
                comment=EcommerceMessage.ERROR_RECEIVER_NOT_APP_ADDR
            ),
            Assert(
                product_pay.get().asset_amount() >= Int(0),
                comment=EcommerceMessage.ERROR_AMOUNT
            ),
            Assert(
                Or(
                    product_pay.get().xfer_asset() == Int(self.__USDC),
                    product_pay.get().xfer_asset() == Int(self.__USDT),
                    product_pay.get().xfer_asset() == Int(self.__STBL2),
                ),
                comment=EcommerceMessage.ERROR_INVALID_TOKEN
            ),
            output.set(EcommerceMessage.OK_PAYMENT_SUCCESSFULL)
        )
    @external(read_only=True)
    def checkUserBalance(self,
                         a: abi.Asset,
                         *, output: abi.Uint64):
        a_id = abi.make(abi.Uint64)
        k = abi.make(abi.Uint8)
        return Seq(
            a_id.set(a.asset_id()),
            k.set(self.getAssetIndex(a_id)),
            output.set(self.user_balance[k][Txn.sender()])
        )

    @external
    def sellerAcceptOrder(self,
                          k: abi.String,
                          *, output: abi.String):
        """Seller update state to be accepted for a specific order"""
        new_state = abi.make(abi.Uint8)
        return Seq(
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            Assert(self.isSeller(), comment=EcommerceMessage.ERROR_USER_IS_NOT_SELLER),
            Assert(self.addrIsSellerInOrder(k), comment=EcommerceMessage.ERROR_INVALID_SELLER_ADDR_ORDER),
            new_state.set(Int(self.ORDER_SELLER_ACCEPTED)),
            self.updateSellerOrderState(k, new_state),
            output.set(EcommerceMessage.OK_ORDER_STATE)
        )
    @external
    def sellerCancelOrder(self,
                          k: abi.String,
                          *, output: abi.String):
        """Seller reject a specific order"""
        return Seq(
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            Assert(self.isSeller(), comment=EcommerceMessage.ERROR_USER_IS_NOT_SELLER),
            Assert(self.addrIsSellerInOrder(k), comment=EcommerceMessage.ERROR_INVALID_SELLER_ADDR_ORDER),
            self.refundBuyer(k),
            output.set(EcommerceMessage.OK_ORDER_STATE)
        )


    @external
    def buyerCompleteOrder(self,
                           k: abi.String,
                           *, output: abi.String):
        """Buyer unlock their money for the seller to take after the order has been delivered."""
        return Seq(
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            Assert(self.addrIsBuyerInOrder(k), comment=EcommerceMessage.ERROR_INVALID_BUYER_ADDR_ORDER),
            Assert(self.getOrderSellerState(k) == Int(self.ORDER_SELLER_ACCEPTED), comment=EcommerceMessage.ERROR_SELLER_NO_ACCEPTED_ORDER),
            self.payoutSeller(k),
            output.set(EcommerceMessage.OK_ORDER_STATE)
        )

    @external
    def buyerCancelOrder(self,
                         k: abi.String,
                         *, output: abi.String):
        """Buyer cancel(or if the seller already accepted it, make a request) for a specific order """
        new_state = abi.make(abi.Uint8)
        return Seq(
            Assert(self.orderExists(k), comment=EcommerceMessage.ERROR_ORDER_DONT_EXIST),
            Assert(self.addrIsBuyerInOrder(k), comment=EcommerceMessage.ERROR_INVALID_BUYER_ADDR_ORDER),
            new_state.set(Int(self.ORDER_BUYER_CANCEL)),
            self.updateBuyerOrderState(k, new_state),
            output.set(EcommerceMessage.OK_ORDER_STATE)
        )
    @external
    def userWithdraw(self,
                     t: abi.Asset,
                     *, output: abi.Uint64):
        """User withdraw tokens"""
        token_index = abi.make(abi.Uint8)
        token_id = abi.make(abi.Uint64)
        balance = abi.make(abi.Uint64)
        addr = abi.make(abi.Address)

        return Seq(
            addr.set(Txn.sender()),
            token_id.set(t.asset_id()),
            token_index.set(self.getAssetIndex(token_id)),
            balance.set(self.user_balance[token_index]),
            Assert(balance.get() >= Int(0), comment=EcommerceMessage.ERROR_NO_FUNDS),
            self.sendStblCoinTo(
                Txn.sender(),
                balance.get(),
                token_id.get(),
                Bytes("User withdraw")
            ),
            output.set(self.decrementUserBalance(addr, balance, token_id)),

        )

class EcommerceMessage:
    """Define default message for the ecommerce application."""

    ERROR_ORDER_EXIST = "The order key already exists"
    ERROR_ORDER_DONT_EXIST = "Order do not exists"
    ERROR_RECEIVER_NOT_APP_ADDR = "The receiver is not the app address"
    ERROR_AMOUNT = "Incorrent Amount"
    ERROR_WRONG_AMOUNT_FEES = "Incorrent amount fees"
    ERROR_NO_FUNDS = "Not enough funds to withdraw"
    ERROR_INVALID_TOKEN = "Not supported token by the smart contract"
    ERROR_USER_IS_SELLER = "The user is already a seller"
    ERROR_INVALID_CREDENTIALS = "Sender is not administrator"

    Ok_ORDER_CREATED ="Order has been created"
    OK_PAYMENT_SUCCESSFULL = "Payment successfull"
    OK_LICENSE_PAYMENT = "License payment successfull"

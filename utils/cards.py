# Visa Gift Card
from transaction import Transaction
from network import BHNRequest, PageParser

class VisaGiftCard:
    """
    Visa Gift Card

    Attributes
    ----------
    * cardNumber(str): 16-digits card number
    * expMonth(str): 2-digit expiration month
    * expYear(str): 2-digit expiration year
    * cvv(str): 3-digit security code
    * postal(str): 5-digit zip code
    * valid(bool): card is valid or not
    * errorMessage(str): error message for invalid card

    Read only properties
    --------------------
    * lastFour(str)
    * cardInfo(dict)
    * initialBalance(float)
    * availableBalance(float)
    * cashback(float)
    * override(float)
    """

    def __init__(self, cardNumber, expirationMonth, expirationYear, cvv, postal):
        self.cardNumber = cardNumber
        self.expMonth = expirationMonth
        self.expYear = expirationYear
        self.cvv = cvv
        self.postal = postal
        self.errorMessage = None
        self.valid = self.validation()

        self.transactions = []
        self.reset()

    @classmethod
    def fromRow(cls, row):
        if len(row) != 6:
            return None
        cardNumber, month, year, cvv, postal, note = row
        return cls(cardNumber, month, year, cvv, postal)

    def reset(self):
        """Reset all attributes getting from network"""
        self._initialBalance = 0.0
        self._availableBalance = 0.0
        self._cashback = 0.0
        self._override = 0.0

    def __str__(self):
        return f'Card {self.lastFour} {self.expMonth}/{self.expYear} cvv:{self.cvv} {self.availableBalance}/{self.initialBalance}'

    def validation(self):
        if len(self.cardNumber) != 16:
            self.errorMessage = 'invalid card number'
            return False

        if self.cardNumber[0] != '4':
            self.errorMessage = 'not a VISA gift card'
            return False

        if len(self.expMonth) == 1:
            self.expMonth = '0' + self.expMonth

        if not (1 <= int(self.expMonth) <= 12):
            self.errorMessage = f'invalid month {self.expMonth}'
            return False

        if not (15 < int(self.expYear) < 100):
            self.errorMessage = f'invalid year {self.expYear}'
            return False

        if not (0 <= int(self.cvv) < 1000):
            self.errorMessage = f'invalid cvv {self.cvv}'
            return False

        self.postal = self.postal or '00000'
        if len(self.postal) != 5:
            self.errorMessage = f'invalid postal {self.postal}'
            return False

        return True

    def getBalanceAndTransactions(self):
        """Get balance through HTTP request. Return a bool representing request success or failure."""
        if not self.valid:
            return False
        self.reset()

        responseStr = BHNRequest(BHNRequest.TypeBalance, self.cardInfo).send()
        parser = PageParser()
        parser.feed(responseStr)

        if parser.initialBalance is None or parser.availableBalance is None:
            self.valid = False
            self.errorMessage = 'card not found'
            return False

        self._initialBalance = parser.initialBalance
        self._availableBalance = parser.availableBalance
        self.transactions = parser.transactions
        for transaction in self.transactions:
            if transaction.transactionType == Transaction.TypeCashback:
                self._cashback += transaction.amount
            elif transaction.transactionType == Transaction.TypeOverride:
                self._override += transaction.amount

        self.valid = True
        self.errorMessage = None
        return True

    def registerCard(self, contactInfo):
        if not self.valid:
            return False
        responseStr = BHNRequest(BHNRequest.TypeRegistation, self.cardInfo, contactInfo).send()
        return 'Your card was successfully registered' in responseStr

    def setPin(self, pinCode):
        if not self.valid:
            return False
        responseStr = BHNRequest(BHNRequest.TypeSetPin, self.cardInfo, None, pinCode).send()
        return 'Your card PIN has been set!' in responseStr

    # Read-only properties

    @property
    def lastFour(self):
        """Return last four digits of card number."""
        return self.cardNumber[-4:]

    @property
    def cardInfo(self):
        """Return JSON dictionary for POST request."""
        json = {
            'CardNumber': self.cardNumber,
            'ExpirationMonth': self.expMonth,
            'ExpirationYear': self.expYear,
            'SecurityCode': self.cvv
        }
        if self.postal != '00000':
            json['PostalCode'] = self.postal
        return json

    @property
    def initialBalance(self):
        """Return initial card balance"""
        return self._initialBalance

    @property
    def availableBalance(self):
        """Return available card balance"""
        return self._availableBalance

    @property
    def cashback(self):
        """Return total cashback amount"""
        return self._cashback

    @property
    def override(self):
        """Return total override amount"""
        return self._override

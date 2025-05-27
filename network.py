from html.parser import HTMLParser  # Python 3 compatible
import requests
import re
from transaction import Transaction

DEBUG = False

class BHNRequest:
    """BHNRequest

    Attributes
    ----------
    *requestType(int): `BHNRequest.TypeBalance`, `BHNRequest.TypeRegister` or `BHNRequest.TypeSetPin`
    *data(dict): JSON dictionary for POST request
    """

    DOMAIN = 'https://mygift.giftcardmall.com/'
    HEADER = {'X-Requested-With': 'XMLHttpRequest', 'Referer': DOMAIN}

    # Request Type Enum
    TypeBalance, TypeRegistation, TypeSetPin = range(0, 3)

    URLS = {
        TypeBalance: 'Card/_Login?returnUrl=Transactions',
        TypeRegistation: ['Card/_Login?returnUrl=Registration', 'Account/_Profile/form-complete-reg?name=complete-reg'],
        TypeSetPin: ['Card/_Login?returnUrl=SetPin', 'Card/_SetPin/setpin-form']
    }

    def __init__(self, requestType, cardInfo, contactInfo=None, pin=None):
        self.requestType = requestType
        self.cardInfo = cardInfo
        self.contactInfo = contactInfo
        self.pinInfo = {
            'PinCode': pin,
            'ConfirmPin': pin
        }

    def send(self):
        """Send a POST request and return response.text"""
        if self.requestType == BHNRequest.TypeBalance:
            url = BHNRequest.DOMAIN + BHNRequest.URLS[self.requestType]
            response = requests.post(url, headers=BHNRequest.HEADER, data=self.cardInfo, verify=not DEBUG)
        else:
            url = BHNRequest.DOMAIN + BHNRequest.URLS[self.requestType][0]
            session = requests.Session()
            response = session.post(url, headers=BHNRequest.HEADER, data=self.cardInfo, verify=not DEBUG)
            if response.url == url:
                return ''  # Registration failed

            if self.requestType == BHNRequest.TypeRegistation:
                data = self.contactInfo
            else:
                match = re.search(r'<input id="CardID" name="CardID" type="hidden" value="(\d+)" \/>', response.text)
                if match:
                    self.pinInfo['CardID'] = match.group(1)
                    data = self.pinInfo
                else:
                    return ''

            url = BHNRequest.DOMAIN + BHNRequest.URLS[self.requestType][1]
            response = session.post(url, headers=BHNRequest.HEADER, data=data, verify=not DEBUG)

        return response.text


class PageParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.availableBalance = None
        self.initialBalance = None
        self.transactions = []

        self.currentTag = None
        self.currentClass = None
        self.currentName = None
        self.transaction = None

    def handle_starttag(self, tag, attrs):
        self.currentTag = tag
        self.currentClass = None
        if attrs:
            attrDict = dict(attrs)
            if 'class' in attrDict:
                self.currentClass = attrDict['class']
                if self.currentClass == 'panel-heading':
                    self.transaction = Transaction()
                elif self.currentClass == 'panel-collapse collapse':
                    self.transactions.append(self.transaction)
                    self.transaction = None

    def handle_data(self, data):
        content = data.strip()
        if content == '':
            return

        moneyStrToFloat = lambda x: float(x.replace('$', ''))

        if self.currentTag == 'div':
            if self.currentClass == 'name':
                self.currentName = content
            elif self.currentClass == 'value':
                if self.currentName == 'Available Balance':
                    self.availableBalance = moneyStrToFloat(content)
                elif self.currentName == 'Initial Balance':
                    self.initialBalance = moneyStrToFloat(content)
                self.currentName = None
            elif self.currentClass and self.currentClass.startswith('col-xs-5ths transaction-'):
                key = self.currentClass.split('-')[-1]
                if key == 'type':
                    self.transaction.typeStr = content
                elif key == 'desc':
                    self.transaction.description = content
                elif key == 'amount':
                    self.transaction.amount = moneyStrToFloat(content)
        elif self.currentTag == 'span' and self.currentClass == 'glyphicon glyphicon-plus':
            self.transaction.dateStr = content

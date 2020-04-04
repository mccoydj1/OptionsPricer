"""This Python script provides examples on using the E*TRADE API endpoints"""
from __future__ import print_function
import webbrowser
import json
import logging
import configparser
import sys
import requests
from rauth import OAuth1Service
from logging.handlers import RotatingFileHandler
from accounts.accounts import Accounts
from market.market import Market

# loading configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# logger settings
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler("python_client.log", maxBytes=5*1024*1024, backupCount=3)
FORMAT = "%(asctime)-15s %(message)s"
fmt = logging.Formatter(FORMAT, datefmt='%m/%d/%Y %I:%M:%S %p')
handler.setFormatter(fmt)
logger.addHandler(handler)

"""Allows user authorization for the sample application with OAuth 1"""
etrade = OAuth1Service(
    name="etrade",
    consumer_key=config["DEFAULT"]["CONSUMER_KEY"],
    consumer_secret=config["DEFAULT"]["CONSUMER_SECRET"],
    request_token_url="https://api.etrade.com/oauth/request_token",
    access_token_url="https://api.etrade.com/oauth/access_token",
    authorize_url="https://us.etrade.com/e/t/etws/authorize?key={}&token={}",
    base_url="https://api.etrade.com")

base_url = config["DEFAULT"]["SANDBOX_BASE_URL"]
#base_url = config["DEFAULT"]["PROD_BASE_URL"]

# Step 1: Get OAuth 1 request token and secret
request_token, request_token_secret = etrade.get_request_token(
    params={"oauth_callback": "oob", "format": "json"})

# Step 2: Go through the authentication flow. Login to E*TRADE.
# After you login, the page will provide a text code to enter.
authorize_url = etrade.authorize_url.format(etrade.consumer_key, request_token)
webbrowser.open(authorize_url)
text_code = input("Please accept agreement and enter text code from browser: ")

# Step 3: Exchange the authorized request token for an authenticated OAuth 1 session
session = etrade.get_auth_session(request_token,
                              request_token_secret,
                              params={"oauth_verifier": text_code})

# URL for the API endpoint
url = base_url + "/v1/market/optionchains.json"
#url = base_url + "/v1/market/optionexpiredate.json"


# Add parameters and header information
params = {"symbol": 'AAPL', 'strikePriceNear':485, 'noOfStrikes': '10'}
headers = {"consumerkey": config["DEFAULT"]["CONSUMER_KEY"]}

# Get Option Prices
response_option = session.get(url, header_auth=True, params=params, headers=headers)

# Get underlying stock price
response_stock = session.get(base_url + "/v1/market/quote/CAT.json")
stockparsed = json.loads(response_stock.text)
quotedata = stockparsed['QuoteResponse']['QuoteData'][0]['All']

valuablefind = list

optionsparsed = json.loads(response_option.text)
for optionpair in optionsparsed['OptionChainResponse']['OptionPair']:
    callprice = optionpair['Call']['lastPrice']
    putprice = optionpair['Put']['lastPrice']
    stockprice = (quotedata['ask'] + quotedata['bid'])/2
    optionstrikeprice = optionpair['Call']['strikePrice']

    # To be risk neutral, need to do one of the two...
    # Sell Call, Buy Put, and Buy stock
    # or
    # Buy Call, Sell Put, and sell stock short

    # Buy strategy
    buystrategy = dict()
    buystrategy['optionsstocksale'] = 100 * optionstrikeprice
    buystrategy['costofstock'] = 100 * stockprice * -1
    buystrategy['optionssale'] = 100 * (callprice - putprice)

    #Net result
    buystrategy['result'] = buystrategy['optionsstocksale'] + buystrategy['costofstock'] + buystrategy['optionssale']

    # Sell strategy
    sellstrategy = dict()
    sellstrategy['optionsstocksale'] = 100 * optionstrikeprice * -1
    sellstrategy['costofstock'] = 100 * stockprice
    sellstrategy['optionssale'] = 100 * (callprice - putprice) * - 1

    # Net result
    sellstrategy['result'] = sellstrategy['optionsstocksale'] + sellstrategy['costofstock'] + sellstrategy['optionssale']

    # Determine if the strategy is a good idea or not...
    callspread = optionpair['Call']['ask'] - optionpair['Call']['bid']
    putspread = optionpair['Put']['ask'] - optionpair['Put']['bid']

    # Determine if option is liquid or not
    thresh_optionvolume = 100        # Volume required on this specific option to be considered safe
    thresh_optionbidsize = 10
    thresh_optionspread = 0.5

    # Params
    volumeokay = (optionpair['Call']['volume'] > thresh_optionvolume) and (optionpair['Put']['volume'] > thresh_optionvolume)
    bidaskokay = (optionpair['Call']['askSize'] > thresh_optionbidsize) and (optionpair['Put']['askSize'] > thresh_optionbidsize)
    spreadokay = (callspread < thresh_optionspread) and (putspread < thresh_optionspread)

    # optionpair['Call']['OptionGreeks']['gamma']
    # optionpair['Put']['OptionGreeks']['gamma']
    # optionpair['Call']['OptionGreeks']['iv']
    # optionpair['Put']['OptionGreeks']['iv']

    if volumeokay and bidaskokay and spreadokay:

        # This strategy will be profitable to execute against
        valuablefind.append([optionpair, buystrategy['result'], sellstrategy['result']])

#session.get(base_url + "/v1/market/quote/CAT")
#session.get(r'https://apisb.etrade.com/v1/market/optionexpiredate?symbol=GOOG&expiryType=ALL')
#!/usr/bin/env python
# coding:utf8

import time
import sys
reload(sys)
sys.setdefaultencoding( "utf8" )
import warnings
warnings.filterwarnings("ignore")
import MySQLdb
import MySQLdb.cursors
import numpy as np
from config import *
import pprint
import random
import pandas as pd
import logging

# ppdai api
from openapi_client import openapi_client as client
from core.rsa_client import rsa_client as rsa
import json
import datetime
import os
from datetime import timedelta

from run import app, time2str, str2time, get_previous_month, get_next_month, connectdb, closedb

OpenID = sys.argv[1]
APPID = sys.argv[2]
AccessToken = sys.argv[3]

try:
	(db,cursor) = connectdb()

	app.logger.error(str(OpenID) + ' history_money ready')

	flag = True
	while True:
		cursor.execute("select status from task where name=%s and OpenID=%s", ['bidBasicInfo', OpenID])
		status = cursor.fetchall()
		if len(status) == 0:
			flag = False
			break
		else:
			status = status[0]['status']

		if status == 'finished':
			break
		else:
			time.sleep(1)

	if flag:
		app.logger.error(str(OpenID) + ' history_money start')

		cursor.execute("select ListingId from listing where OpenID=%s", [OpenID])
		ListingIds = cursor.fetchall()
		ListingIds = [x['ListingId'] for x in ListingIds]

		if len(ListingIds) > 0:
			cursor.execute("delete from lender where ListingId in %s", [ListingIds])
		many = []
		finished = 0
		for x in range(0, len(ListingIds), 5):
			if x + 5 <= len(ListingIds):
				y = x + 5
			else:
				y = len(ListingIds)
			while True:
				time.sleep(0.5)
				access_url = "http://gw.open.ppdai.com/invest/LLoanInfoService/BatchListingBidInfos"
				data = {"ListingIds": ListingIds[x:y]}
				sort_data = rsa.sort(data)
				sign = rsa.sign(sort_data)
				list_result = client.send(access_url, json.dumps(data), APPID, sign)
				if list_result == '':
					continue
				list_result = json.loads(list_result)
				for item in list_result['ListingBidsInfos']:
					finished += 1
					for i in item['Bids']:
						many.append([item['ListingId'], i['LenderName'], i['BidAmount'], i['BidDateTime']])

				if len(many) >= 500:
					cursor.executemany("insert into lender(ListingId, LenderName, BidAmount, BidDateTime) values(%s, %s, %s, %s)", many)					
					del many[:]

				cursor.execute("update task set history_money=%s where name=%s and OpenID=%s",['total_' + str(len(ListingIds)) + '_finished_' + str(finished), 'bidBasicInfo', OpenID])
				break

		if len(many) > 0:
			cursor.executemany("insert into lender(ListingId, LenderName, BidAmount, BidDateTime) values(%s, %s, %s, %s)", many)					

		cursor.execute("update task set m0=%s, timestamp=%s where name=%s and OpenID=%s", [1, int(time.time()), 'bidBasicInfo', OpenID])

		closedb(db,cursor)

		app.logger.error(str(OpenID) + ' history_money finish')
except Exception, e:
	app.logger.error(e)
else:
	pass
finally:
	pass
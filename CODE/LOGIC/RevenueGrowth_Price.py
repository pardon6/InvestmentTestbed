# _*_ coding: utf-8 _*_

import os
import sys
import warnings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
warnings.filterwarnings("ignore")

import pandas as pd
import math
from datetime import datetime
from datetime import timedelta
from datetime import date
from itertools import count

from COMM import DB_Util
from COMM import File_Util
from COMM import CALC_Util


# Wrap운용팀 DB Connect
db = DB_Util.DB()
db.connet(host="127.0.0.1", port=3306, database="investing.com", user="root", password="ryumaria")


start_date = '2016-01-01'
sql = "WITH tmp AS (" \
"SELECT a.pid AS pid" \
"     , a.date AS date" \
"     , a.eps_fore AS eps_fore" \
"     , a.eps_bold AS eps_bold" \
"     , a.revenue_fore AS revenue_fore" \
"     , a.revenue_bold AS revenue_bold" \
"     , (CASE @p_pid WHEN a.pid THEN @p_date ELSE @p_date:='' END) AS p_date" \
"     , (CASE @p_pid WHEN a.pid THEN format(@p_eps_fore,2) ELSE @p_eps_fore:=0 END) AS p_eps_fore" \
"     , (CASE @p_pid WHEN a.pid THEN format(@p_eps_bold,2) ELSE @p_eps_bold:=0 END) AS p_eps_bold" \
"     , (CASE @p_pid WHEN a.pid THEN format(@p_revenue_fore,0) ELSE @p_revenue_fore:=0 END) AS p_revenue_fore" \
"     , (CASE @p_pid WHEN a.pid THEN format(@p_revenue_bold,0) ELSE @p_revenue_bold:=0 END) AS p_revenue_bold" \
"     , (@p_pid:=a.pid)" \
"	  , (@p_date:=a.date)" \
"	  , (@p_eps_fore:=a.eps_fore)" \
"	  , (@p_eps_bold:=a.eps_bold)" \
"	  , (@p_revenue_fore:=a.revenue_fore)" \
"	  , (@p_revenue_bold:=a.revenue_bold)" \
"  FROM stock_earnings a" \
"     , (select @p_pid:='', @p_date:='', @p_eps_fore:=0 , @p_eps_bold:=0 , @p_revenue_fore:=0, @p_revenue_bold:=0 from dual) b" \
" WHERE a.date > '%s')" \
"SELECT a.pid AS pid" \
"	  , a.date AS date" \
"	  , a.eps_fore AS eps_fore" \
"	  , a.eps_bold AS eps_bold" \
"	  , a.revenue_fore AS revenue_fore" \
"	  , a.revenue_bold AS revenue_bold" \
"	  , a.p_date AS p_date" \
"	  , a.p_eps_fore AS p_eps_fore" \
"	  , a.p_eps_bold AS p_eps_bold " \
"	  , a.p_revenue_fore AS p_revenue_fore" \
"	  , a.p_revenue_bold AS p_revenue_bold" \
"	  , b.close AS price" \
"	  , c.close AS p_price" \
"	  , b.close/c.close-1 AS rate" \
"  FROM tmp a" \
"     , stock_price b" \
"     , stock_price c" \
" WHERE a.pid = b.pid" \
"   AND a.date = b.date" \
"   AND a.pid = c.pid" \
"   AND a.p_date = c.date"% (start_date)
print(sql)
raw_data = db.select_query(query=sql)
#raw_data.drop(columns=[11,12,13,14,15,16], inplace=True)
raw_data.columns = ['pid','date','eps_fore','eps_bold','revenue_fore','revenue_bold','p_date','p_eps_fore','p_eps_bold','p_revenue_fore','p_revenue_bold','price','p_price','rate']
raw_data['acc_revenue_bold'] = 0.0
print(raw_data)

pivoted_revenue_bold = raw_data.pivot(index='date', columns='pid', values='revenue_bold')
#print(pivoted_revenue_bold)
pivoted_revenue_fore = raw_data.pivot(index='date', columns='pid', values='revenue_fore')
#print(pivoted_revenue_fore)

count_new_data = 0
term_size = 4
arr_revenue_bold = [0.0] * term_size
for row in raw_data.iterrows():
    idx = row[0]
    data = row[1]

    arr_revenue_bold[:term_size-1] = arr_revenue_bold[-(term_size-1):]

    if idx > 0:
        if data['pid'] != prev_pid:
            count_new_data = 0
            arr_revenue_bold = [0.0] * term_size

    else:
        count_new_data = 0
        arr_revenue_bold = [0.0] * term_size

    arr_revenue_bold[-1] = float(data['revenue_bold'] if (data['revenue_bold'] != None and data['revenue_bold'] != 0) else sum(arr_revenue_bold[:term_size-1])/(term_size-1))

    count_new_data += 1

    if count_new_data >= term_size:
        raw_data['acc_revenue_bold'][idx] = sum(arr_revenue_bold) / term_size

    prev_pid = data['pid']

raw_data['acc_revenue_bold_chg'] = raw_data['acc_revenue_bold'].pct_change()
print(raw_data)
File_Util.SaveCSVFiles(obj_dict=raw_data)


db.disconnect()

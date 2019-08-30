# _*_ coding: utf-8 _*_

import urllib
import urllib.request
import requests
from urllib.error import HTTPError

from bs4 import BeautifulSoup
from selenium import webdriver
import datetime
import time
import sys
from itertools import count
import arrow
import re
import timeit
import pandas as pd
from datetime import datetime
from datetime import timedelta
from datetime import date


def getRealValue(s):
    try:
        if len(s) == 0:
            value = 'NULL'
            unit = 'NULL'
        else:
            s = s.replace(',', '')
            if s[-1].upper() == 'K':
                value = float(s[:-1])
                unit = 1000
            elif s[-1].upper() == 'M':
                value = float(s[:-1])
                unit = 1000000
            elif s[-1].upper() == 'B':
                value = float(s[:-1])
                unit = 1000000000
            elif s[-1] == '%':
                value = float(s[:-1])
                unit = 0.01
            elif s[-1] == '-':
                value = 0.0
                unit = 1
            else:
                value = float(s)
                unit = 1

        return value, unit

    except (ValueError, TypeError) as e:
        print('에러정보 : ', e, file=sys.stderr)

        return None, None


class Good():
    def __init__(self):
        self.value = "+"
        self.name = "good"

    def __repr__(self):
        return "<Good(value='%s')>" % (self.value)


class Bad():
    def __init__(self):
        self.value = "-"
        self.name = "bad"

    def __repr__(self):
        return "<Bad(value='%s')>" % (self.value)


class Unknow():
    def __init__(self):
        self.value = "?"
        self.name = "unknow"

    def __repr__(self):
        return "<Unknow(value='%s')>" % (self.value)


class InvestingEconomicCalendar():
    def __init__(self, uri='https://www.investing.com/economic-calendar/', country_list=None):
        self.uri = uri
        self.req = urllib.request.Request(uri)
        self.req.add_header('User-Agent',
                            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36')
        self.country_list = country_list
        self.result = []

    def getEvents(self):
        try:
            response = urllib.request.urlopen(self.req)
            html = response.read()
            soup = BeautifulSoup(html, "html.parser")

            # Find event item fields
            table = soup.find('table', {"id": "economicCalendarData"})
            tbody = table.find('tbody')
            rows = tbody.findAll('tr', {"class": "js-event-item"})

            for row in rows:
                events = {}
                _datetime = row.attrs['data-event-datetime']
                events['timestamp'] = arrow.get(_datetime, "YYYY/MM/DD HH:mm:ss").timestamp
                events['date'] = _datetime[0:10]

                cols = row.find('td', {"class": "flagCur"})
                flag = cols.find('span')
                events['country'] = flag.get('title')

                # 예외 국가 필터링
                if self.country_list is not None and events['country'] not in self.country_list:
                    continue

                impact = row.find('td', {"class": "sentiment"})
                bull = impact.findAll('i', {"class": "grayFullBullishIcon"})
                events['impact'] = len(bull)

                event = row.find('td', {"class": "event"})
                a = event.find('a')
                events['url'] = "{}{}".format(self.uri, a['href'][a['href'].find('/', 2) + 1:])
                events['name'] = a.text.strip()

                # Determite type of event
                events['type'] = None
                if event.find('span', {"class": "smallGrayReport"}):
                    events['type'] = "report"
                elif event.find('span', {"class": "audioIconNew"}):
                    events['type'] = "speech"
                elif event.find('span', {"class": "smallGrayP"}):
                    events['type'] = "release"
                elif event.find('span', {"class": "sandClock"}):
                    events['type'] = "retrieving data"

                bold = row.find('td', {"class": "bold"})
                events['bold'] = bold.text.strip() if bold.text != '' else ''

                fore = row.find('td', {"class": "fore"})
                events['fore'] = fore.text.strip() if fore.text != '' else ''

                prev = row.find('td', {"class": "prev"})
                events['prev'] = prev.text.strip() if prev.text != '' else ''

                if "blackFont" in bold['class']:
                    events['signal'] = Unknow()
                elif "redFont" in bold['class']:
                    events['signal'] = Bad()
                elif "greenFont" in bold['class']:
                    events['signal'] = Good()
                else:
                    events['signal'] = Unknow()

                print(events)
                self.result.append(events)

        except HTTPError as error:
            print("Oops... Get error HTTP {}".format(error.code))

        return self.result


calendar_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
              , 'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}

def CrawlingStart(obj):
    obj.Start()

class InvestingEconomicEventCalendar():
    def __init__(self, econmic_event_list, db):
        self.economic_event_list = econmic_event_list
        self.db = db
        self.options = webdriver.ChromeOptions()
        if 0:
            self.options.add_argument('headless')
            self.options.add_argument('window-size=1920x1080')
            self.options.add_argument("disable-gpu")
            # 혹은 options.add_argument("--disable-gpu")

        self.wd = webdriver.Chrome('chromedriver', chrome_options=self.options)
        #self.wd = webdriver.Chrome('/Users/sangjinryu/Downloads/chromedriver', chrome_options=self.options)

        self.wd.get('https://www.investing.com')
        time.sleep(60)

    def Start(self, t_gap=0.2, loop_num=float('inf')):
        startTime = timeit.default_timer()

        for data in self.economic_event_list.iterrows():
            cd = data[1]['cd']
            nm = data[1]['nm_us']
            link = data[1]['link']
            ctry = data[1]['ctry']
            period = data[1]['period']
            type = data[1]['type']

            # 배치가 중간에 중단된 경우 문제가 발생한 Event 이후부터 시작
            if cd < 0:
                # if cd not in (81,228,303,331,461,484,569,596,868,889,914,1037,1038,1040,1315,1468,1524,1526,1533,1534,1548,1571,1581,1650,1746,1747,1748,1751,1755,1762,1763,1765,1771,1772,1777,1793,1801,1810,1811,1812,1813,1820,1821,1878,1887,1913):
                print('continue: ', nm, link)
                continue

            # Event별 Schedule 리스트 크롤링
            cralwing_nm, results = self.GetEventSchedule(link, cd, t_gap, loop_num)
            print(cd, nm, cralwing_nm, link, len(results))

            type_in_nm = 'Ori'
            if 'WoW' in cralwing_nm:
                type_in_nm = 'WoW'
            elif 'MoM' in cralwing_nm:
                type_in_nm = 'MoM'
            elif 'QoQ' in cralwing_nm:
                type_in_nm = 'QoQ'
            elif 'YoY' in cralwing_nm:
                type_in_nm = 'YoY'

            # 크롤링된 Event 이름으로 변경
            if nm != cralwing_nm or type != type_in_nm:
                sql = "UPDATE economic_events" \
                      "   SET nm_us='%s'" \
                      "     , type='%s'" \
                      " WHERE cd=%s"
                sql_arg = (cralwing_nm, type_in_nm, cd)
                print(sql % sql_arg)
                if (self.db.execute_query(sql, sql_arg) == False):
                    #print(sql % sql_arg) # update 에러 메세지를 보여준다.
                    pass
            # print(results)

            pre_statistics_time = 0
            # 시계역 역순(가장 최근 데이터가 처음)
            for cnt, result in enumerate(results):
                try:
                    date_rlt = result['date']
                    date_splits = re.split('\W+', date_rlt)
                    date_str = str(date(int(date_splits[2]), calendar_map[date_splits[0]], int(date_splits[1])))

                    # 통계시점에 대한 정보가 없는 경우 주기가 monthly인 경우 처리
                    statistics_time = 'NULL' if len(date_splits) <= 3 or date_splits[3] not in calendar_map.keys() else \
                        calendar_map[date_splits[3]]
                    if period == 'M':
                        # 첫 데이터인 경우 이전달의 값을 역으로 추정
                        if pre_statistics_time == 0:
                            pre_statistics_time = statistics_time + 1 if statistics_time < 12 else 1

                        # 통계시점에 대한 정보가 없는 경우에 이전 데이터에 대한 정보를 사용해서 추정
                        if statistics_time == 'NULL':
                            statistics_time = pre_statistics_time - 1 if pre_statistics_time > 1 else 12

                        pre_statistics_time = statistics_time

                    time = result['time']
                    # GDP처럼 추정치가 먼저 발표되는 경우
                    pre_release_yn = result['pre_release_yn']

                    bold = result['bold']
                    fore = result['fore']
                    prev = result['prev']

                    # 단위가 K, M, %으로 다양하여 실제 수치로 변경
                    bold_value, bold_unit = getRealValue(result['bold'])
                    bold_flt = bold_value * bold_unit if bold_value != 'NULL' or bold_unit != 'NULL' else 'NULL'
                    fore_value, fore_unit = getRealValue(result['fore'])
                    fore_flt = fore_value * fore_unit if fore_value != 'NULL' or fore_unit != 'NULL' else 'NULL'
                    print(cd, '\t', date_str, '\t', bold_unit)

                    sql = "INSERT INTO economic_events_schedule (event_cd, release_date, release_time, statistics_time, bold_value, fore_value, pre_release_yn, create_time, update_time) " \
                          "VALUES (%s, '%s', '%s', %s, %s, %s, %s, now(), now()) " \
                          "ON DUPLICATE KEY UPDATE release_time = '%s', statistics_time = %s, bold_value = %s, fore_value = %s, pre_release_yn = %s, update_time = now()"
                    sql_arg = (
                        cd, date_str, time, statistics_time, bold_flt, fore_flt, pre_release_yn, time, statistics_time,
                        bold_flt, fore_flt, pre_release_yn)

                    if (self.db.execute_query(sql, sql_arg) == False):
                        # print(sql % sql_arg) # insert 에러 메세지를 보여준다.
                        pass

                except (TypeError, KeyError) as e:
                    print('에러정보 : ', e, file=sys.stderr)
                    print(date_splits, pre_statistics_time)

            endTime = timeit.default_timer()
            print("Cnt:", str(cnt), "\tElapsed time: ", str(endTime - startTime))


    def GetEventSchedule(self, url, cd, t_gap, loop_num):

        self.wd.get(url)

        RESULT_DIRECTORY = '__results__/crawling'
        results = []
        loop_cnt = 0
        for page in count(1):
            try:
                # 정해진 횟수만 크롤링
                if loop_cnt >= loop_num:
                    raise Exception('loop_cnt: ' % loop_cnt)
                else:
                    loop_cnt += 1

                script = 'void(0)'  # 사용하는 페이지를 이동시키는 js 코드
                # self.wd.execute_script(script)  # js 실행
                result = self.wd.find_element_by_xpath('//*[@id="showMoreHistory%s"]/a' % cd)
                result.click()

                time.sleep(t_gap)  # 크롤링 로직을 수행하기 위해 5초정도 쉬어준다.
            except:
                # print('error: %s' % str(page))

                html = self.wd.page_source
                bs = BeautifulSoup(html, 'html.parser')
                nm = bs.find('body').find('section').find('h1').text.strip()
                tbody = bs.find('tbody')
                rows = tbody.findAll('tr')

                for row in rows:
                    tmp_rlt = {}

                    times = row.findAll('td', {'class': 'left'})
                    tmp_rlt['date'] = times[0].text.strip()
                    tmp_rlt['time'] = times[1].text.strip()
                    tmp_rlt['pre_release_yn'] = 1 if times[1].find('span') != None and times[1].find('span')['title'] == "Preliminary Release" else 0

                    values = row.findAll('td', {'class': 'noWrap'})
                    tmp_rlt['bold'] = values[0].text.strip()
                    tmp_rlt['fore'] = values[1].text.strip()
                    tmp_rlt['prev'] = values[2].text.strip()
                    # print(tmp_rlt)

                    results.append(tmp_rlt)

                return nm, results


class IndiceHistoricalData():

    def __init__(self, API_url):
        self.API_url = API_url

        # set https header parameters
        headers = {
            'User-Agent': 'Mozilla/5.0',  # required
            'referer': "https://www.investing.com",
            'host': 'www.investing.com',
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.headers = headers

    # set indice data (indices.py)
    def setFormData(self, data):
        self.data = data

    # prices frequency, possible values: Monthly, Weekly, Daily
    def updateFrequency(self, frequency):
        self.data['frequency'] = frequency

    # desired time period from/to
    def updateStartingEndingDate(self, startingDate, endingDate):
        self.data['st_date'] = startingDate
        self.data['end_date'] = endingDate

    # possible values: 'DESC', 'ASC'
    def setSortOreder(self, sorting_order):
        self.data['sort_ord'] = sorting_order

    # making the post request
    def downloadData(self):
        self.response = requests.post(self.API_url, data=self.data, headers=self.headers).content
        # parse tables with pandas - [0] probably there is only one html table in response
        self.observations = pd.read_html(self.response)[0]
        return self.observations

    # print retrieved data
    def printData(self):
        print(self.observations)

    # print retrieved data
    def saveDataCSV(self):
        self.observations.to_csv(self.data['name'] + '.csv', sep='\t', encoding='utf-8')
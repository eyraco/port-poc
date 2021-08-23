""" Script to extract info from Google Browser History """

__version__ = '0.1.0'

import json
import re
import zipfile
from datetime import datetime
import pandas as pd


START = datetime(2021, 1, 23, 21)
END = datetime(2021, 4, 28, 4, 30)
TEXT = f"""
With this research we want to invesitgate how our news consumption \
behavior has changed during/after the COVID-19 related curfew. \
To examine this, we looked at your Google Search History.
First, we divided your browser history into three periods:
- before the start of the curfew (i.e., pages visited before {START}),
- during the curfew (i.e., pages visited between {START} and {END}), and
- post curfew (i.e., pages visited after {END}).
For each period, we counted how many times you visited a news \
website versus any another type of website (i.e., news/other). \
While counting, we also took the time of day \
(i.e., morning/afternoon/evening/night) into account.
"""
NEWSSITES = 'news.google.com|nieuws.nl|nos.nl|www.rtlnieuws.nl|nu.nl|\
    at5.nl|ad.nl|bd.nl|telegraaf.nl|volkskrant.nl|parool.nl|\
    metronieuws.nl|nd.nl|nrc.nl|rd.nl|trouw.nl'


def __calculate(dates):
    """Counts number of web searches per time unit (morning, afternoon,
        evening, night), per website-period combination
    Args:
        dates: dictionary, dates per website (news vs. other) per period
            (pre, during, post curfew)
    Returns:
        results: list, number of times websites are visted per unit of time
    """
    results = []
    for category in dates.keys():
        sub = {'morning': 0, 'afternoon': 0,
               'evening': 0, 'night': 0}
        sub['Curfew'], sub['Website'] = category.split('_')
        for date in dates[category]:
            hour = date.hour
            if 0 <= hour < 6:
                sub['night'] += 1
            elif 6 <= hour < 12:
                sub['morning'] += 1
            elif 12 <= hour < 18:
                sub['afternoon'] += 1
            elif 18 <= hour < 24:
                sub['evening'] += 1
        results.append(sub)
    return results


def __extract(data):
    """Extracts relevant data from browser history:
        - number of times websites (news vs. other) are visited
        - at which specific periods (pre, during, and post curfew),
        - on which specific times a day (morning, afternoon, evening, night).
    Args:
        data: BrowserHistory.json file
    Returns:
        results: list, number of times websites are visted per unit of time,
            per moment
        earliest: datetime, earliest web search
        latest: datetime, latest web search
    """
    # Count number of news vs. other websites per time period
    # (i.e., pre/during/after Dutch curfew)
    dates = {'before_news': [], 'during_news': [], 'post_news': [],
             'before_other': [], 'during_other': [], 'post_other': []}
    earliest = datetime.today()
    latest = datetime(2000, 1, 1)
    for data_unit in data["Browser History"]:
        if data_unit["page_transition"].lower() != 'reload':
            time = datetime.fromtimestamp(data_unit["time_usec"]/1e6)
            if time < earliest:
                earliest = time
            if time > latest:
                latest = time
            if time < START and re.findall(NEWSSITES, data_unit["url"]):
                dates['before_news'].append(time)
            elif time > END and re.findall(NEWSSITES, data_unit["url"]):
                dates['post_news'].append(time)
            elif time < START and not re.findall(NEWSSITES, data_unit["url"]):
                dates['before_other'].append(time)
            elif time > END and not re.findall(NEWSSITES, data_unit["url"]):
                dates['post_other'].append(time)
            elif re.findall(NEWSSITES, data_unit["url"]):
                dates['during_news'].append(time)
            elif not re.findall(NEWSSITES, data_unit["url"]):
                dates['during_other'].append(time)
    # Calculate times visited per time unit
    # (i.e., morning, afternoon, evening, night)
    results = __calculate(dates)
    return results, earliest, latest


def process(file_data):
    """ Opens BrowserHistory.json and return relevant data pre, during,
        and post Dutch curfew
    Args:
        file_data: Takeout zipfile
    Returns:
        summary: summary of read file(s), earliest and latest websearch
        data_frames: pd.dataframe, overview of news vs. other searches
            per moment per time unit
    """
    # Read BrowserHistory.json
    with zipfile.ZipFile(file_data) as zfile:
        file_list = zfile.namelist()
        for name in file_list:
            if re.search('BrowserHistory.json', name):
                data = json.loads(zfile.read(name).decode("utf8"))
    # Extract pre/during/post website searches,
    # earliest webclick and latest webclick
    results, earliest, latest = __extract(data)
    # Make tidy dataframe of webclicks
    df_results = pd.melt(pd.json_normalize(results), ["Curfew", "Website"],
                         var_name="Time", value_name="Searches")
    data_frame = df_results.sort_values(
        ['Curfew', 'Website']).reset_index(drop=True)
    # Return output
    text = f"""{TEXT}
    read_files: BrowserHistory.json
    Your earliest web search was on {earliest},
    The Dutch curfew took place between {START} and {END},
    Your latest web search was on {latest}.
    """
    return {
        "summary": text,
        "data_frames": [
            data_frame
        ]
    }
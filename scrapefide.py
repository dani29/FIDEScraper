__author__ = "Dani Raznikov"
__email__ = "daniraznikov29@gmail.com"
import csv
import time
import logging
import argparse

import requests
from bs4 import BeautifulSoup


# Mapping between p and dP, taken from FIDE Handbook:
# https://www.fide.com/component/handbook/?id=174&view=article
PERFORMANCE_TABLE = {
    1.0: 800, 0.99: 677, 0.98: 589, 0.97: 538, 0.96: 501, 0.95: 470, 0.94: 444,
    0.93: 422, 0.92: 401, 0.91: 383, 0.9: 366, 0.89: 351, 0.88: 336, 0.87: 322,
    0.86: 309, 0.85: 296, 0.84: 284, 0.83: 273, 0.82: 262, 0.81: 251, 0.8: 240,
    0.79: 230, 0.78: 220, 0.77: 211, 0.76: 202, 0.75: 193, 0.74: 184, 0.73: 175,
    0.72: 166, 0.71: 158, 0.70: 149, 0.69: 141, 0.68: 133, 0.67: 125, 0.66: 117,
    0.65: 110, 0.64: 102, 0.63: 95, 0.62: 87, 0.61: 80, 0.6: 72, 0.59: 65,
    0.58: 57, 0.57: 50, 0.56: 43, 0.55: 36, 0.54: 29, 0.53: 21, 0.52: 14, 0.51: 7,
    0.5: 0, 0.49: -7, 0.48: -14, 0.47: -21, 0.46: -29, 0.45: -36, 0.44: -43,
    0.43: -50, 0.42: -57, 0.41: -65, 0.4: -72, 0.39: -80, 0.38: -87, 0.37: -95,
    0.36: -102, 0.35: -110, 0.34: -117, 0.33: -125, 0.32: -133, 0.31: -141,
    0.3: -149, 0.29: -158, 0.28: -166, 0.27: -175, 0.26: -184, 0.25: -193,
    0.24: -202, 0.23: -211, 0.22: -220, 0.21: -230, 0.2: -240, 0.19: -251,
    0.18: -262, 0.17: -273, 0.16: -284, 0.15: -296, 0.14: -309, 0.13: -322,
    0.12: -336, 0.11: -351, 0.1: -366, 0.09: -383, 0.08: -401, 0.07: -422,
    0.06: -444, 0.05: -470, 0.04: -501, 0.03: -538, 0.02: -589, 0.01: -677, 0: -800
}

TRN_NAME_COLOR = '#CC9966'
TRN_SCORE_COLOR = '#e6e6e6'
NO_RECORDS_STRING = 'No records found in individual calculations for this period.'

csv_fields = ['Rating Period',
              'Tournament Name',
              'City',
              'Country',
              'Pts.',
              'Rds.',
              'Avg. Opponents',
              'Rtg. Change',
              'Performance']

LOGIN_URL = "https://ratings.fide.com/login_action.php"
CALCULATION_URL = "https://ratings.fide.com/individual_calculations.phtml?" \
    "idnumber={id}&rating_period={year}-{month:02d}-01&t=0"


def get_rating_urls(player_id, months=12):
    """Generating a list of URLs for each of the last 
    rating reports.

    :arg player_id: FIDE player ID
    :arg months:    Number of months to check

    :return urls:   List of URLs to scrape
    """
    urls = []
    now = time.localtime()
    periods = [time.localtime(time.mktime(
        (now.tm_year, now.tm_mon - n, 1, 0, 0, 0, 0, 0, 0)))[:2]
        for n in range(months)]
    for y, m in periods:
        urls.append(CALCULATION_URL.format(id=player_id,
                                           year=y,
                                           month=m))

    return urls


def calc_performance(avg, pts, rds):
    """Calcluate performance using FIDE's performance formula.
    Perf = AvgRtg + Rating Difference, whose values is defined in the 
    PerformanceTable values.

    :arg avg:   Opponents AVG rating
    :arg pts:   Points Scored
    :arg rds:   Games played

    :return perf: FIDE rating Performance value.
    """
    if type(pts) == int:
        pts = float(pts)

    score = round(pts / rds, 2)
    perf = avg + PERFORMANCE_TABLE[score]
    return perf


def scrape_rating_reports(urls):
    """Scraping the rating reports from the provided URL list,
    Using BeautifulSoup to parse each table.

    :arg urls: List of URLs to scrape

    :return tournaments: List of dicts that represent tournaments
    """

    tournaments = []

    for url in urls:

        # Perform Login for each page
        s = requests.Session()
        payload = {'fd_user': 'fidescraper',
                   'fd_password': 'beautifulsoup'}
        login = s.post(LOGIN_URL, data=payload)
        resp = s.get(url)
        html_doc = resp.content
        soup = BeautifulSoup(html_doc, "html.parser")
        result = soup.findAll('table', {'class': 'contentpaneopen'})
        period = result[0].text.replace(
            '\n', '').replace(
            'Individual Calculations ', '')[:-1]

        if result[1].text.replace('\n', '') == NO_RECORDS_STRING:
            print('%s No Records!' % period)
            continue

        print('Scraping %s...' % period)

        # Scrape each table row based on the bgcolor value
        # The tournament header and scores have distinct
        # background colors
        trn_headers = result[1].findAll('tr', {'bgcolor': TRN_NAME_COLOR})
        trn_scores = result[1].findAll('tr', {'bgcolor': TRN_SCORE_COLOR})
        if len(trn_headers) != len(trn_scores):
            raise RuntimeError(
                'Size of tournament headers list must be equal to' /
                'the size of tournament scores list.')

        for i in range(len(trn_headers)):
            trn_name, city, country, date = [
                x.text.replace(u'\xa0', '') for x in trn_headers[i]]
            opp_avg, ply_rtg, pts, rds, chg, kFactor, rating_change, _ = [
                x.text.replace(u'\xa0', '') for x in trn_scores[i]]

            new_tourn = {'Rating Period': period,
                         'Tournament Name': trn_name,
                         'City': city,
                         'Country': country,
                         'Pts.': float(pts),
                         'Rds.': int(rds),
                         'Avg. Opponents': int(opp_avg),
                         'Rtg. Change': float(rating_change)}
            performance = calc_performance(avg=new_tourn['Avg. Opponents'],
                                           pts=new_tourn['Pts.'],
                                           rds=new_tourn['Rds.'])
            new_tourn['Performance'] = performance
            tournaments.append(new_tourn)

        time.sleep(1)

    return tournaments


def write_to_csv(player_id, tournaments):
    """Writes the tournaments list to csv output.

    :arg player_id:     FIDE player ID
    :arg tournaments:   List of dicts that represent tournaments

    """
    with open('%s.csv' % player_id, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()

        for trn in tournaments:
            writer.writerow(trn)


def configure_arg_parser(parser):
    parser.add_argument('--id', '-i',
                        required=True,
                        help='FIDE Player ID')
    parser.add_argument('--months', '-m',
                        required=False,
                        default=12, type=int,
                        help='How many months to report for')
    return parser


def main():
    parser = argparse.ArgumentParser()
    configure_arg_parser(parser)
    args = parser.parse_args()
    urls = get_rating_urls(args.id, args.months)
    tournaments = scrape_rating_reports(urls)
    write_to_csv(args.id, tournaments)

if __name__ == '__main__':
    main()

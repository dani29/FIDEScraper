# FIDEScraper
Scraping FIDE ratings profile to create a report of players' performance in a given timeframe.

# Usage #
1. Clone the repo and install the requirements.txt file using pip.
2. Run `python scrapefide.py` with the following arguments:
  * `--id/-i <FIDE_Player_ID>` to specify which player you would like to find.
  * `--months/-m <Num>`        to specify how many months to consider (defaults to 12).
3. Check the output file in `<PlayerID>.csv`

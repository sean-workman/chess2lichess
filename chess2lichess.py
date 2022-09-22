import argparse
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import os
import re
import requests
from time import sleep


# -----------------------------------GLOBALS-----------------------------------#

# Sets the lichess token based on an an environment variable named
# LICHESS_TOKEN
LICHESS_TOKEN = os.getenv("LICHESS_TOKEN")

# Dictionary for filter game type
TIME_CONTROL = {"rapid": "600", "blitz": "180", "bullet": "60"}

# ------------------------------------CLASS------------------------------------#


class Chess2Lichess:
    def __init__(self, username, verbose) -> None:
        self.username = username
        self.verbose = verbose

    def fetch_current_month(self) -> list:
        """
        Uses the requests library to fetch the raw multi-game PGN text for
        games played in the month that the script is being run in. Returns a UTF-8
        encoded string.
        """
        url = f"https://api.chess.com/pub/player/{self.username}/games/{(today:=datetime.today()):%Y}/{today:%m}/pgn"
        headers = {
            "content_type": "application/x-chess-pgn",
            "Content-Disposition": f'attachment; filename="ChessCom_{self.username}_{today:%Y%m}.pgn"',
        }
        response = requests.get(url=url, headers=headers)
        response.raise_for_status()
        pgns = response.text
        pgn_list = pgns.split("\n\n\n")
        return pgn_list

    def fetch_month(self, date: str) -> list:
        """
        Uses the requests library to fetch the raw multi-game PGN text for
        games played in the specified month. Returns a UTF-8 encoded string.
        """
        year, month = date.split("/")
        url = (
            f"https://api.chess.com/pub/player/{self.username}/games/{year}/{month}/pgn"
        )
        headers = {
            "content_type": "application/x-chess-pgn",
            "Content-Disposition": f'attachment; filename="ChessCom_{self.username}_{year}{month}.pgn"',
        }
        response = requests.get(url=url, headers=headers)
        response.raise_for_status()
        pgns = response.text
        pgn_list = pgns.split("\n\n\n")
        return pgn_list

    def fetch_range(self, start_in: str, end_in: str) -> str:
        """
        Uses the requests library to fetch the raw multi-game PGN text for
        games played in the specified month. Returns a UTF-8 encoded string.
        """
        month_list = []

        start_year, start_month = start_in.split("/")
        end_year, end_month = end_in.split("/")
        start = date(int(start_year), int(start_month), 1)
        end = date(int(end_year), int(end_month), 1)

        while start <= end:
            month_list.append(start)
            start += relativedelta(months=1)

        pgn_accumulator = []

        for m in month_list:
            url = f"https://api.chess.com/pub/player/{self.username}/games/{m.year}/{m.month:02d}/pgn"
            headers = {
                "content_type": "application/x-chess-pgn",
                "Content-Disposition": f'attachment; filename="ChessCom_{self.username}_{m.year}{m.month:02d}.pgn"',
            }
            response = requests.get(url=url, headers=headers)
            response.raise_for_status()
            pgn_accumulator.append(response.text)

        return pgn_accumulator

    def filter_pgns(self, pgn_list: list, game_types: str) -> list:
        """
        Filters PGNs fetched from chess.com based on time control.
        """
        if self.verbose:
            print(f"Filtering to only include {', '.join(game_types)} games...")
        tc_pattern = re.compile(r"TimeControl \"(\d+[\+\d+]{0,3})\"")
        durations = [TIME_CONTROL[gt] for gt in game_types]
        filtered_pgn_list = []
        for pgn in pgn_list:
            if re.search(tc_pattern, pgn).group(1).split("+")[0] in durations:
                filtered_pgn_list.append(pgn)
        if not filtered_pgn_list:
            print("There are no games that pass the filter!")
        else:
            return filtered_pgn_list

    def import_pgns(self, pgn_list: list) -> None:
        """
        Uses the requests library to post the PGN text to the lichess.org server,
        imports it into your profile.
        """
        url = "https://lichess.org/api/import"
        headers = {
            "content_type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {LICHESS_TOKEN}",
        }
        n_games = len(pgn_list)
        games_imported = 0
        if self.verbose:
            print(f"There are {len(pgn_list)} games to import")
            print("Importing games from chess.com...")
        for pgn in pgn_list:
            data = {"pgn": pgn}
            # response = requests.post(url=url, headers=headers, data=data)
            # response.raise_for_status()
            games_imported += 1
            if self.verbose:
                print(f"Imported {games_imported}/{n_games}")
            if games_imported != n_games:
                sleep(7.5)
        if self.verbose:
            print("Finished importing games from chess.com")


# -----------------------------------PARSING-----------------------------------#

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "username",
        help="the chess.com username of the profile you want to download games from",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="show information about number of games and progress",
    )

    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "-c",
        "--current",
        action="store_true",
        help="import chess.com games from the current month to lichess.org",
    )
    modes.add_argument(
        "-m",
        "--month",
        nargs=1,
        metavar="YYYY/MM",
        help="import chess.com games from the specified month to lichess.org",
    )
    modes.add_argument(
        "-r",
        "--range",
        nargs=2,
        metavar="YYYY/MM",
        help="import chess.com games from months in the specified range to lichess.org",
    )

    parser.add_argument(
        "-f",
        "--filter",
        nargs="*",
        help="filter which game types are imported - space separated",
        metavar="TYPE",
    )

    args = parser.parse_args()

    c2l = Chess2Lichess(args.username, args.verbose)

    if args.current:
        pgns = c2l.fetch_current_month()
    elif args.month:
        pgns = c2l.fetch_month(args.month[0])
    elif args.range:
        pgns = c2l.fetch_range(args.range[0], args.range[1])

    if args.filter:
        pgns = c2l.filter_pgns(pgns, args.filter)

    if pgns:
        c2l.import_pgns(pgns)

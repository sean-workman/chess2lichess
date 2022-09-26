import argparse
import csv
from datetime import date, datetime
from dateutil import tz
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

# Creates the regex pattern used downstream to pull out the individual pieces
# of information to store in the local "database".
TAGS = [
    "(?s)",
    '(White "(?P<white>\S+)")',
    '(Black "(?P<black>\S+)")',
    '(UTCDate "(?P<date>\d+.\d+.\d+)")',
    '(UTCTime "(?P<time>\d+:\d+:\d+)")',
    '(WhiteElo "(?P<white_elo>\d+)")',
    '(BlackElo "(?P<black_elo>\d+)")',
    '(TimeControl "(?P<time_control>\d+[\+\d+]{0,3})")',
    '(Termination "(?P<termination>(\S+\s){,10}\w+)")',
    "(Link .+/live/(?P<game_id>\d+))",
]

TAG_PATTERN = re.compile(".+".join(TAGS))

# Creating variables for downstream timezone correction
UTC_ZONE = tz.tzutc()
LOCAL_ZONE = tz.tzlocal()

# ------------------------------------CLASS------------------------------------#


class Chess2Lichess:
    def __init__(self, username, verbose, convert_local) -> None:
        self.username = username
        self.verbose = verbose
        self.convert_local = convert_local

    def check_db_existence(self) -> None:
        """
        Check if .csv "database" exists and creates it if not
        """
        if not os.path.exists("pgn_database.csv"):
            with open("pgn_database.csv", "wt") as database:
                print(
                    "Created local 'database' named pgn_database.csv in the current directory"
                )
                writer = csv.writer(database)
                writer.writerow(
                    [
                        "game_id",
                        "game_date",
                        "game_time",
                        "white",
                        "white_elo",
                        "black",
                        "black_elo",
                        "time_control",
                        "termination",
                    ]
                )

    def convert_utc_to_local(self, date, time):
        """
        Takes in the UTC date and time as written in the PGN text fetched from the
        chess.com server, returns a tuple of date and time as string with the
        formatting (YYYY/MM/DD, HH:MM:SS).
        """
        utc = datetime.strptime(f"{date} {time}", "%Y.%m.%d %H:%M:%S")
        utc = utc.replace(tzinfo=UTC_ZONE)
        local = utc.astimezone(LOCAL_ZONE)
        date, time = datetime.strftime(local, "%Y/%m/%d %H:%M:%S").split()
        return date, time

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

    def fetch_range(self, start_in: str, end_in: str) -> list:
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

        pgn_accumulator = ""
        for m in month_list:
            url = f"https://api.chess.com/pub/player/{self.username}/games/{m.year}/{m.month:02d}/pgn"
            headers = {
                "content_type": "application/x-chess-pgn",
                "Content-Disposition": f'attachment; filename="ChessCom_{self.username}_{m.year}{m.month:02d}.pgn"',
            }
            response = requests.get(url=url, headers=headers)
            response.raise_for_status()
            pgn_accumulator += response.text.rstrip()
            pgn_accumulator += "\n\n\n"

        pgn_list = pgn_accumulator.rstrip("\n\n\n").split("\n\n\n")

        return pgn_list

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
            print("There are no games that pass your filter!")
            exit(1)
        else:
            return filtered_pgn_list

    def check_already_imported(self, fetched_pgns: list) -> list:
        """
        Check local monthly PGN text document to see which games have already
        been imported. Return a sanitized list of PGNs that have not yet been
        imported.
        """
        with open("pgn_database.csv", "r+") as file:
            reader = csv.reader(file)
            current_ids = [row[0] for row in reader]
        print(f"{len(fetched_pgns)} games requested for import")
        if len(current_ids) > 1:
            unseen_pgns = [
                pgn
                for pgn in fetched_pgns
                if re.search(TAG_PATTERN, pgn).group("game_id") not in current_ids
            ]
            dont_import = len(fetched_pgns) - len(unseen_pgns)
        else:
            unseen_pgns = fetched_pgns
            dont_import = 0
        if not unseen_pgns:
            print("All requested games have already been imported!")
            exit(1)
        else:
            if self.verbose:
                print(
                    f"{dont_import} of the {len(fetched_pgns)} requested games have already been imported"
                )
            return unseen_pgns

    def update_db(self, pgn) -> None:
        """
        Update the local .csv "database" with PGN tags for each game being imported.
        """
        with open("pgn_database.csv", "a+") as database:
            writer = csv.writer(database)
            tags = re.search(TAG_PATTERN, pgn)
            game_id = tags.group("game_id")
            if self.convert_local:
                game_date, game_time = self.convert_utc_to_local(
                    tags.group("date"), tags.group("time")
                )
            else:
                game_date, game_time = (tags.group("date"), tags.group("time"))
            white = tags.group("white")
            white_elo = tags.group("white_elo")
            black_elo = tags.group("black_elo")
            black = tags.group("black")
            time_control = tags.group("time_control")
            termination = tags.group("termination")

            writer.writerow(
                [
                    game_id,
                    game_date,
                    game_time,
                    white,
                    white_elo,
                    black,
                    black_elo,
                    time_control,
                    termination,
                ]
            )

    def update_local_pgns(self, pgn, last=False) -> None:
        """
        Update the local PGN text document with each game being imported.
        """
        with open("local_pgns.txt", "a+") as file:
            if not last:
                file.write(pgn + "\n\n\n")
            else:
                file.write(pgn + "\n\n")

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
            try:
                requests.post(url=url, headers=headers, data=data)
                games_imported += 1
            except requests.exceptions.HTTPError:
                print("Too many requests - pausing imports for one minute")
                sleep(60)
                requests.post(url=url, headers=headers, data=data)
                games_imported += 1
            self.update_db(pgn)
            if pgn != pgn_list[-1]:
                self.update_local_pgns(pgn)
            else:
                self.update_local_pgns(pgn, last=True)
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

    parser.add_argument(
        "-f",
        "--filter",
        nargs="*",
        help="filter which game types are imported - space separated",
        metavar="TYPE",
    )

    parser.add_argument(
        "-u",
        "--utc",
        action="store_false",
        default=True,
        help="stop the script from converting date/time from UTC to local timezone",
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

    args = parser.parse_args()

    # Instantiate Chess2Liches object
    c2l = Chess2Lichess(args.username, args.verbose, convert_local=args.utc)

    # Check for existence of 'database', create if necessary
    c2l.check_db_existence()

    # Fetch requested PGNs
    if args.current:
        pgns = c2l.fetch_current_month()
    elif args.month:
        pgns = c2l.fetch_month(args.month[0])
    elif args.range:
        pgns = c2l.fetch_range(args.range[0], args.range[1])
    # Filter PGNs on time control if requested
    if args.filter:
        pgns = c2l.filter_pgns(pgns, args.filter)

    # Check to see which PGNs have already been imported
    pgns = c2l.check_already_imported(pgns)
    # Import the requested games to lichess.org
    c2l.import_pgns(pgns)

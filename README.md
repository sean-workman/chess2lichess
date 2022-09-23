# Chess.com to Lichess.org PGN Importer

Programmatically import games played on chess.com to lichess.org via PGN text.

I am really bad at chess and trying to be less bad at programming. I made this script as a little weekend project to practice the programming side of things.

Using this script, you can import all games from chess.com into your lichess.org profile in the current month that the script is being run in, from a specified month, or from a range of months. I plan on implementing an option to maintain a local "database" in .csv format in order to make some fun graphs showing how bad at chess I am in fun and interesting ways. I might just uncover hidden patterns in how bad I am at chess. I made this to import my own chess.com games to lichess.org, but in theory you could import the games from any user you might like.

Let me know if there are bugs or features you would actually want added here.

P.S. If there are a lot of games, the script will take a while to run. I have limited it to one POST request every 7.5 seconds so as not to overload the lichess.org servers and raise a 429 error. I recommend running it with the -v/--verbose option in order to keep track of the progress.

## Setup

1. Obtain a lichess.org OAuth2 token - I granted my token full access, honestly not entirely sure what limited options are required for game import: https://lichess.org/account/oauth/token

2. Set an environment variable called "LICHESS_TOKEN"

3. `git clone https://github.com/sean-workman/chess2lichess` OR let's be honest, just download the script and put it wherever you want on your machine.

4. Ensure that you have installed both the requests library and dateutil module in your working environment. 

## Usage

```
python chess2lichess.py username [-h] [-v] (-c | -m YYYY/MM | -r YYYY/MM YYYY/MM)

positional arguments:
  username              the chess.com username of the profile you want to download games from

options:
  -h, --help            show this help message and exit
  -v, --verbose         show information about number of games and progress
  -f [TYPE ...], --filter [TYPE ...]
                        filter which game types are imported - space separated
  -u, --utc             stop the script from converting date/time from UTC to local timezone
  -c, --current         import chess.com games from the current month to lichess.org
  -m YYYY/MM, --month YYYY/MM
                        import chess.com games from the specified month to lichess.org
  -r YYYY/MM YYYY/MM, --range YYYY/MM YYYY/MM
                        import chess.com games from months in the specified range to lichess.org
```

## Examples

`python chess2lichess.py hikaru -v -m 2022/08`

The above command would fetch and import all 363 games that GM Hikaru played on chess.com in the month of August 2022 and let you know about the progress as it goes.

`python chess2lichess.py hikaru -v -m 2022/08 -f blitz`

The above command would fetch and import all 238 blitz games that GM Hikaru played on chess.com in the month of August 2022 and let you know about the progress as it goes.

`python chess2lichess.py hikaru -v -m 2022/08 -f blitz bullet`

The above command would fetch and import all 238 blitz games and 83 bullet games that GM Hikaru played on chess.com in the month of August 2022 and let you know about the progress as it goes.

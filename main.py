import datetime as dt
import toml
from pprint import pprint
from os import path
from sys import argv

aDay = dt.timedelta(days=1)

CONFIG_FILE__NAME = "conf.toml"
CONFIG_FILE__FIELDS = [
    ('hoursPlanned', int),
    ('minutesPlanned', int),
]
HISTORY_FILE__NAME = "log.txt"

def create_file(filename):
    with open(filename, "w"):
        pass


def getATPS():
    def parse_time_period(hours, minutes):
        def validate(duration, upper_bound, lower_bound = 0):
            return lower_bound <= duration <= upper_bound

        try:
            hours, minutes = int(hours), int(minutes)
            hours += minutes // 60
            minutes %= 60

            assert validate(hours, 24) and validate(minutes, 60)
            assert dt.timedelta(hours=hours, minutes=minutes) < aDay
            return hours, minutes

        except (ValueError, AssertionError):
            print('Invalid input')
            exit()


    hours, minutes = input('\tHours: '), input('\tMinutes: ')

    return parse_time_period(hours, minutes)

def create_config():
    print('-- SETUP --\n\n? Planned rest per day')

    hoursPlanned, minutesPlanned = getATPS()

    config = dict(
        hoursPlanned = hoursPlanned,
        minutesPlanned = minutesPlanned
    )

    with open(CONFIG_FILE__NAME, 'w') as cfile:
        toml.dump(config, cfile)

def get_config():
    if not path.exists(CONFIG_FILE__NAME):
        create_config()

    config = toml.load(CONFIG_FILE__NAME)

    for field_name, field_type in CONFIG_FILE__FIELDS:
        if not isinstance(config.get(field_name), field_type):
            print('!!! Config file is corrupped')
            create_config()
            config = toml.load(CONFIG_FILE__NAME)
            break

    return config

def get_history():
    

    if not path.exists(HISTORY_FILE__NAME):
        create_file(HISTORY_FILE__NAME)

    with open(HISTORY_FILE__NAME, "r") as log_file:
        return list(line.rstrip('\n') for line in log_file.readlines())

def process_clargs():
    if len(argv) > 1 and "reset-config" in argv:
        create_config()

class Duration:
    def _validate(self):
        pass

    

def main():
    process_clargs()

    config = get_config()
    history = get_history()

    restPerDay = dt.timedelta(hours=config['hoursPlanned'], minutes=config['minutesPlanned'])

    pprint(config)
    pprint(history)

if __name__ == "__main__":
    main()
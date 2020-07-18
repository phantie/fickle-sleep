import datetime as dt
import toml
from pprint import pprint
from os import path

aDay = dt.timedelta(days=1)

def getATPS():
    def parse_time_period(hours, minutes):
        def validate(duration, upper_bound, lower_bound = 0):
            return lower_bound <= duration <= upper_bound

        try:
            hours, minutes = int(hours), int(minutes)
            hours += minutes // 60
            minutes -= minutes // 60

            assert validate(hours, 24) and validate(minutes, 60)
            assert dt.timedelta(hours=hours, minutes=minutes) < aDay
            return hours, minutes

        except (ValueError, AssertionError):
            print('Invalid input')
            exit()


    hours, minutes = input('\tHours: '), input('\tMinutes: ')

    return parse_time_period(hours, minutes)

def get_config():
    CONFIG_FILE__NAME = "conf.toml"
    CONFIG_FILE__FIELDS = [
        ('hoursPlanned', int),
        ('minutesPlanned', int),
    ]

    def create_config():
        print('-- SETUP --\n\n? Time you are planning to sleep per day')

        hoursPlanned, minutesPlanned = getATPS()

        config = dict(
            hoursPlanned = hoursPlanned,
            minutesPlanned = minutesPlanned
        )

        with open(CONFIG_FILE__NAME, 'w+') as cfile:
            toml.dump(config, cfile)

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


def main():
    config = get_config()
    restPerDay = dt.timedelta(hours=config['hoursPlanned'], minutes=config['minutesPlanned'])
    pprint(config)

if __name__ == "__main__":
    main()
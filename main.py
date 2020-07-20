import datetime as dt
import toml
from pprint import pprint
from os import path
# from sys import argv
from enum import Enum, auto
from dataclasses import dataclass, asdict

aDay = dt.timedelta(days=1)
datetime_fmt = "%d-%m-%Y, %H:%M:%S"

CONFIG_FILE__NAME = "conf.toml"
LOG_FILE__NAME = "log.txt"



@dataclass
class Config:
    hoursPlanned: int
    minutesPlanned: int

class Act(Enum):
    asleep = "asleep"
    awake = "awake"

@dataclass
class LogRow:
    state: Act
    time: dt.datetime

    def as_str(self):
        return f'{self.state.value} {self.time.strftime(datetime_fmt)}\n'

def get_config_data():
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

    print('? Planned rest per day')
    hours, minutes = input('\tHours: '), input('\tMinutes: ')
    hours, minutes = parse_time_period(hours, minutes)
    
    config = Config(
        hoursPlanned=hours,
        minutesPlanned=minutes,
    )

    return config

def create_config():
    print(': SETUP\n')

    config_data = asdict(get_config_data())

    with open(CONFIG_FILE__NAME, 'w') as cfile:
        toml.dump(config_data, cfile)

def get_config():
    if not path.exists(CONFIG_FILE__NAME):
        create_config()

    _config = toml.load(CONFIG_FILE__NAME)

    for field_name, field in Config.__dataclass_fields__.items():
        if not isinstance(_config.get(field_name), field.type):
            print('! Config file is corrupped')
            create_config()
            _config = toml.load(CONFIG_FILE__NAME)
            break
    
    config = Config(**_config)

    return config

def parse_row(row):
    state, time = row.rstrip('\n').split(maxsplit=1)
    for state_name, _state in Act.__members__.items():
        if state_name == state:
            state: Act = _state
            break
    else:
        raise Exception("Not valid state", state)
    
    time: dt.datetime = dt.datetime.strptime(time, datetime_fmt)

    return LogRow(state=state, time=time)

def safe_parse_row(row):
    try:
        return parse_row(row)
    except:
        return ""

def create_file(filename):
    with open(filename, "w"):
        pass

def get_log():
    if not path.exists(LOG_FILE__NAME):
        create_file(LOG_FILE__NAME)

    with open(LOG_FILE__NAME, "r") as log_file:
        log = list(parse_row(row) for row in log_file.readlines())

    return log


### It won`t save againts drastical
### manual log interuption. So don`t.
def repair_log():
    assert path.exists(LOG_FILE__NAME)

    repaired_rows = []

    with open(LOG_FILE__NAME, "r") as log_file:
        for row in log_file.readlines():
            if parsed := safe_parse_row(row):
                repaired_rows.append(parsed)

    if len(repaired_rows) > 0 and repaired_rows[-1].state is not Act.awake:
        del repaired_rows[-1]

    rewrite_log(repaired_rows)


# def process_clargs():
#     if len(argv) > 1 and "reset-config" in argv:
#         create_config()


def calculate_fraction_of_day(var):
    assert var < aDay

    return var.seconds / (24 * 60 ** 2)


def welcome_cli():
    print(
        "Welcome. Please select:\n"
        "1. Calculate sleep duration for now.\n"
        "2. Slept significantly less or more last time? \n Reflect it in the log.\n"
        "3. Reset configuration.\n"
        "4. Repair log\n"
        "5. Exit.\n"
        )
    
    num = input("Enter: ")

    if num.isnumeric() and int(num) in range(1, 5):
        num = int(num)
        if num == 1:
            pass
        elif num == 2:
            pass
        elif num == 3:
            create_config()
        elif num == 4:
            repair_log()
        elif num == 5:
            print("Bye")
            exit()
    else:
        print("Invalid input")
        exit()

def append_to_log(log_row: LogRow):
    assert isinstance(log_row, LogRow)

    with open(LOG_FILE__NAME, 'a') as log_file:
        log_file.write(log_row.as_str())

def rewrite_log(log):
    with open(LOG_FILE__NAME, 'w') as log_file:
        log_file.writelines(map(lambda self: self.as_str(), log))


def get_asleep_awake(time: dt.timedelta):
    start = dt.datetime.now()
    end = start + time
    asleep = LogRow(state=Act.asleep, time=start)
    awake = LogRow(state=Act.awake, time=end)
    return asleep, awake

def calculate_amount_of_sleep(log):
    pass


def main():
    welcome_cli()

    config = get_config()
    log = get_log()

    rest_per_day = dt.timedelta(hours=config.hoursPlanned, minutes=config.minutesPlanned)

    fraction = calculate_fraction_of_day(rest_per_day)

    print(f'{fraction=}')
    print(f'{config=}')
    print(f'{log=}')

    asleep, awake = get_asleep_awake(dt.timedelta(hours=8))

    # append_to_log(asleep)
    # append_to_log(awake)

    # rewrite_log(log)


if __name__ == "__main__":
    main()
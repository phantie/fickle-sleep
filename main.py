import datetime as dt
import toml
from pprint import pprint
from os import path
# from sys import argv
from enum import Enum, auto
from dataclasses import dataclass, asdict

aDay = dt.timedelta(days=1)
now = dt.datetime.now

datetime_fmt = "%d-%m-%Y, %H:%M:%S"

CONFIG_FILE__NAME = "conf.toml"
LOG_FILE__NAME = "log.txt"


@dataclass
class Config:
    time_planned: int #seconds

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
            assert (tp := dt.timedelta(hours=hours, minutes=minutes)) < aDay

            return tp

        except (ValueError, AssertionError):
            print('Invalid input')
            exit()

    print('? Planned rest per day')
    hours, minutes = input('\tHours: '), input('\tMinutes: ')
    tp = parse_time_period(hours, minutes)

    config = Config(
        time_planned = tp.seconds,
    )

    return config

def create_config():
    print(': SETUP\n')

    config_data = asdict(get_config_data())

    with open(CONFIG_FILE__NAME, 'w') as cfile:
        toml.dump(config_data, cfile)

def get_config():
    def load_config():
        return toml.load(CONFIG_FILE__NAME)

    if not path.exists(CONFIG_FILE__NAME):
        create_config()

    _config = load_config()

    for field_name, field in Config.__dataclass_fields__.items():
        if not isinstance(_config.get(field_name), field.type):
            print('! Config file is corrupped')
            create_config()
            _config = load_config()
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
        raise Exception("Invalid state", state)
    
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
### manual log interruption. So don`t.
def repair_log():
    assert path.exists(LOG_FILE__NAME)

    repaired_records = []

    with open(LOG_FILE__NAME, "r") as log_file:
        for row in log_file.readlines():
            if record := safe_parse_row(row):
                repaired_records.append(record)

    if len(repaired_records) > 0 and repaired_records[-1].state is not Act.awake:
        del repaired_records[-1]

    rewrite_log(repaired_records)


# def process_clargs():
#     if len(argv) > 1 and "reset-config" in argv:
#         create_config()


def fraction_of(divisible, divider):
    assert divisible <= divider

    return divisible / divider

def welcoming():
    this_hour = now().hour

    if 4 <= this_hour <= 11:
        return "morning"
    elif 12 <= this_hour <= 16:
        return "afternoon"
    elif 17 <= this_hour <= 20:
        return "evening"
    elif 21 <= this_hour <= 3:
        return "night"



def welcome_cli():
    print(
        f"Good {welcoming()}. Please select:\n"
        "1. Calculate sleep duration.\n"
        "2. Correct last sleep session.\n"
        "3. Reset configuration.\n"
        "4. Repair log\n"
        "5. Exit.\n"
        )
    
    num = input("Enter: ")

    if num.isnumeric() and (num := int(num)) in range(1, 6):
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
    start = now()
    end = start + time
    asleep = LogRow(state=Act.asleep, time=start)
    awake = LogRow(state=Act.awake, time=end)
    return asleep, awake

def calculate_amount_of_sleep(log, take_by = .4 * aDay):
    def get_latest_records():
        start_moment = now() - take_by
        for i, record in enumerate(log):
            if record.time >= start_moment:
                if record.state is Act.awake:
                    latest_records = log[i-1:]
                elif record.state is Act.asleep:
                    latest_records = log[i:]

                # take_by = start_moment - log[i-1].time
                break

        for record in latest_records:
            print(record)

        return latest_records

    def get_latest_sleep_amount(records):
        total_sleep = dt.timedelta()
        # print(total_sleep)
        for i in range(0, len(records), 2):
            total_sleep += records[i+1].time - records[i].time

        print(total_sleep)

    take_by = take_by
    latest_records = get_latest_records()
    latest_sleep_amount = get_latest_sleep_amount(latest_records)



def main():
    # welcome_cli()

    config = get_config()
    log = get_log()

    rest_per_day = dt.timedelta(seconds=config.time_planned)

    fraction = fraction_of(rest_per_day, aDay)

    print(f'{fraction=}')
    # print(f'{config=}')
    # print(f'{log=}')

    asleep, awake = get_asleep_awake(rest_per_day)

    calculate_amount_of_sleep(log)

    # append_to_log(asleep)
    # append_to_log(awake)

    # rewrite_log(log)


if __name__ == "__main__":
    main()
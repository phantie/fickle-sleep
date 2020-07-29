from datetime import datetime as dt, timedelta, date
from models import Act, LogRow
from utils import print, now
from constants import aDay


def calculate_amount_of_sleep(log, rest_per_day, time_limiter = 4 * aDay):

    def get_latest_records(log):
        nonlocal time_limiter
        begin = now()
        start_moment = begin - time_limiter

        if log:
            for i, record in enumerate(log):
                if record.time >= start_moment:
                    if record.state is Act.awake:
                        log = log[i-1:]
                    elif record.state is Act.asleep:
                        log = log[i:]

                    time_limiter = begin - log[0].time
                    break
        return log

    def get_sleep_amount(records):
        total = timedelta()
        for i in range(0, len(records), 2):
            total += records[i+1].time - records[i].time

        return total

    def get_awake_amount(records):
        records.append(
            LogRow(
                state=Act.asleep,
                time=now()
            )
        )

        total = timedelta()
        for i in range(1, len(records), 2):
            assert records[i+1].time > records[i].time
            # print('Awake from', records[i].time, "to", records[i+1].time, 'Delta:', records[i+1].time - records[i].time)
            total += records[i+1].time - records[i].time

        return total

    def get_timeline(records):
        assert records
        return records[0].time, records[-1].time

    def get_timeline_delta(records):
        start, end = get_timeline(records)
        return end - start

    if latest_records := get_latest_records(log):
        latest_sleep_amount = get_sleep_amount(latest_records)
        latest_awake_amount = get_awake_amount(latest_records)

        gap = get_timeline_delta(latest_records)

        assert gap == latest_sleep_amount + latest_awake_amount

        print("Gap", gap)
        print("Slept", latest_sleep_amount)
        print("Was awake", latest_awake_amount)

        result = ((rest_per_day / aDay) * gap - latest_sleep_amount) / (1 - (rest_per_day / aDay))
    else:
        result = rest_per_day

    return result

from datetime import datetime
from pathlib import Path
from pm4py.objects.log.obj import EventLog
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.filtering.log.timestamp import timestamp_filter

def load_log(file_path: Path) -> EventLog | None:
    try:
        return xes_importer.apply(str(file_path))
    except Exception as exc:
        return None

def first_event_names(log: EventLog) -> list[str]:
    return sorted({trace[0]["concept:name"] for trace in log if trace})

def filter_by_first_event(log: EventLog, event: str) -> EventLog:
    if not event:
        return log
    filtered = EventLog()
    for trace in log:
        if trace and trace[0]["concept:name"] == event:
            filtered.append(trace)
    return filtered

def filter_by_dates(log: EventLog, start: datetime | None, end: datetime | None) -> EventLog:
    if not start and not end:
        return log
    params = {}
    if start:
        params["start_timestamp"] = datetime.combine(start, datetime.min.time())
    if end:
        params["end_timestamp"] = datetime.combine(end, datetime.max.time())
    return timestamp_filter.apply(log, parameters=params)

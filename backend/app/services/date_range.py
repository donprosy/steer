"""Shared date-range parsing for business reports and transaction lists."""

from datetime import datetime, time, timedelta, timezone


def parse_date_range(args, default="this_month"):
    range_name = (args.get("range") or default).strip().lower()
    now = datetime.now(timezone.utc)
    today = now.date()
    if range_name == "today":
        return datetime.combine(today, time.min, timezone.utc), now
    if range_name == "this_week":
        start = today - timedelta(days=today.weekday())
        return datetime.combine(start, time.min, timezone.utc), now
    if range_name == "this_month":
        start = today.replace(day=1)
        return datetime.combine(start, time.min, timezone.utc), now
    if range_name == "this_year":
        start = today.replace(month=1, day=1)
        return datetime.combine(start, time.min, timezone.utc), now
    if range_name != "custom":
        raise ValueError(
            "Range must be today, this_week, this_month, this_year, or custom."
        )

    start_value = args.get("start_date")
    end_value = args.get("end_date")
    if not start_value or not end_value:
        raise ValueError("Custom date ranges require both start_date and end_date.")
    try:
        start = datetime.fromisoformat(start_value.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError("Enter valid ISO 8601 start_date and end_date values.") from error
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if len(end_value) == 10:
        end += timedelta(days=1, microseconds=-1)
    if start > end:
        raise ValueError("start_date must be earlier than or equal to end_date.")
    return start, end

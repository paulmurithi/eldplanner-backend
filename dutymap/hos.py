import math
from datetime import timedelta, datetime

# Constants from the assessment
DRIVING_MAX_PER_DAY = 11.0   # hours driving allowed per 14 hour window
DRIVING_WINDOW_HOURS = 14.0
BREAK_AFTER_HOURS = 8.0      # required 30-min break after 8 cumulative driving hours
BREAK_DURATION = 0.5         # hours
PICKUP_DROP_DURATION = 1.0   # hours each
FUEL_RANGE_MILES = 1000      # fuel stop every 1000 miles
CYCLE_MAX = 70.0             # 70 hours / 8 days assumption

# A helper to split a long route (distance miles, duration hours) into daily legs that obey HOS
def plan_stops_and_logs(total_miles, total_driving_hours, step_points, current_cycle_used_hours):
    """
    Inputs:
      total_miles (float), total_driving_hours (float)
      step_points: list of dicts with {'name', 'lat','lon','distance_from_start_mi','duration_hrs_from_start'}
      current_cycle_used_hours: hours already used in current 8-day cycle (float)
    Returns:
      {
        'days': [
           {
             'date': 'YYYY-MM-DD',
             'events':[{'type':'drive'|'on_duty'|'sleep'|'fuel'|'pickup'|'dropoff'|'break', 'start_hours_from_trip_start', 'duration_hours', 'miles', 'where':name}]
           }
        ],
        'notes': ...
      }
    """
    days = []
    hours_remaining_to_drive = total_driving_hours
    miles_remaining = total_miles
    trip_start = datetime.utcnow().replace(minute=0,second=0,microsecond=0)
    # We'll do a greedy per-day simulation:
    current_time = 0.0  # hours from trip_start
    trip_miles_done = 0.0
    step_index = 0

    # compute fuel stop mile markers
    fuel_markers = set()
    next_fuel = FUEL_RANGE_MILES
    while next_fuel < total_miles:
        fuel_markers.add(round(next_fuel,1))
        next_fuel += FUEL_RANGE_MILES

    day_index = 0
    while trip_miles_done < total_miles - 0.001:
        day = {'date': (trip_start + timedelta(days=day_index)).strftime('%Y-%m-%d'),
               'events': []}
        # driver must have 10 consecutive hours off before starting; for simulation we assume they've had it before start
        # For each day we can drive up to DRIVING_MAX_PER_DAY hours (driving) within a 14-hour window
        day_driving_done = 0.0
        day_on_duty_done = 0.0
        driving_since_last_break = 0.0

        # first if pickup is at start of trip, count pickup hour
        if day_index == 0:
            # pickup event
            day['events'].append({'type':'pickup','start':current_time,'duration':PICKUP_DROP_DURATION,'miles':0.0,'where': step_points[0]['name'] if step_points else 'pickup'})
            current_time += PICKUP_DROP_DURATION
            day_on_duty_done += PICKUP_DROP_DURATION

        # simulate driving chunks until we reach day's driving allowance or trip end
        while trip_miles_done < total_miles - 0.001 and day_driving_done < DRIVING_MAX_PER_DAY - 1e-6:
            # estimate rate mph = total_miles / total_driving_hours
            avg_speed = total_miles / max(total_driving_hours, 0.1)
            remaining_driving_capacity = DRIVING_MAX_PER_DAY - day_driving_done
            # drive a chunk until next fuel marker or until remaining_driving_capacity (convert to miles)
            chunk_hours = min(remaining_driving_capacity, 1.0)  # drive in 1-hour chunks for granularity
            chunk_miles = chunk_hours * avg_speed
            # if next fuel marker is within this chunk, shorten to reach fuel marker
            next_fuel_mile = min([m for m in fuel_markers if m > trip_miles_done] + [total_miles])
            if trip_miles_done + chunk_miles >= next_fuel_mile - 0.001 and next_fuel_mile < total_miles:
                # drive to fuel marker
                chunk_miles = next_fuel_mile - trip_miles_done
                chunk_hours = chunk_miles / max(avg_speed, 1e-6)
            # apply chunk
            day['events'].append({'type':'drive','start':current_time,'duration':chunk_hours,'miles':chunk_miles,'where': None})
            current_time += chunk_hours
            day_driving_done += chunk_hours
            day_on_duty_done += chunk_hours
            driving_since_last_break += chunk_hours
            trip_miles_done += chunk_miles
            # if chunk ended at fuel marker, insert fuel + 30-min on-duty (refuel counted as on duty)
            if round(trip_miles_done,1) in fuel_markers:
                day['events'].append({'type':'fuel','start':current_time,'duration':0.5,'miles':0.0,'where':'fuel_stop'})
                current_time += 0.5
                day_on_duty_done += 0.5
            # if driving_since_last_break >= 8 -> insert 30-minute break
            if driving_since_last_break >= BREAK_AFTER_HOURS - 1e-6:
                day['events'].append({'type':'break','start':current_time,'duration':BREAK_DURATION,'miles':0.0,'where':'rest_break'})
                current_time += BREAK_DURATION
                day_on_duty_done += BREAK_DURATION
                driving_since_last_break = 0.0
        # at end of day, include 10 hours off-duty to reset next start; but for log drawing we show off-duty as 10 hours
        day['events'].append({'type':'sleep','start':current_time,'duration':10.0,'miles':0.0,'where':'off_duty_sleep'})
        current_time += 10.0
        days.append(day)
        day_index += 1

    # finally add dropoff event at last day end (1 hour)
    days[-1]['events'].append({'type':'dropoff','start':current_time,'duration':PICKUP_DROP_DURATION,'miles':0.0,'where': step_points[-1]['name'] if step_points else 'dropoff'})
    return {'days':days}

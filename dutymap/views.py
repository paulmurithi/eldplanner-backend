import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import PlanTripInputSerializer, TripSerializer
from .models import Trip
from .hos import plan_stops_and_logs
from django.conf import settings

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_ROUTE = "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson&steps=true"

def geocode(addr):
    # Accept "lat,lon" and short-circuit
    if ',' in addr:
        try:
            lat, lon = [float(x.strip()) for x in addr.split(',')]
            return {'lat': lat, 'lon': lon, 'display_name': addr}
        except:
            pass
    params = {'q': addr, 'format': 'json', 'limit': 1}
    r = requests.get(NOMINATIM_URL, params=params, headers={"User-Agent":"ELDPlanner/1.0"})
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError("Address not found: "+addr)
    item = data[0]
    return {'lat': float(item['lat']), 'lon': float(item['lon']), 'display_name': item.get('display_name')}

@api_view(['POST'])
def plan_trip(request):
    serializer = PlanTripInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    # geocode each
    a = geocode(data['current_location'])
    b = geocode(data['pickup_location'])
    c = geocode(data['dropoff_location'])

    coords = f"{a['lon']},{a['lat']};{b['lon']},{b['lat']};{c['lon']},{c['lat']}"
    route_url = OSRM_ROUTE.format(coords=coords)
    r = requests.get(route_url, timeout=10)
    if r.status_code != 200:
        return Response({'error':'route failed','details':r.text}, status=500)
    route = r.json()

    # extract total distance (meters) and duration (seconds)
    route_summary = route['routes'][0]
    total_meters = route_summary['distance']
    total_seconds = route_summary['duration']
    total_miles = total_meters / 1609.34
    total_hours = total_seconds / 3600.0

    # build step points for remarks and step-level names
    step_points = []
    # include pickup and dropoff names
    step_points.append({'name':'Current Location','lat':a['lat'],'lon':a['lon'],'distance_from_start_mi':0.0,'duration_hrs_from_start':0.0})
    step_points.append({'name':'Pickup: '+b['display_name'],'lat':b['lat'],'lon':b['lon'],'distance_from_start_mi':None,'duration_hrs_from_start':None})
    step_points.append({'name':'Dropoff: '+c['display_name'],'lat':c['lat'],'lon':c['lon'],'distance_from_start_mi':total_miles,'duration_hrs_from_start':total_hours})

    # plan daily logs
    logs = plan_stops_and_logs(total_miles, total_hours, step_points, data['current_cycle_used_hours'])

    # return
    out = {
        'route_geojson': route_summary['geometry'],
        'distance_miles': total_miles,
        'duration_hours': total_hours,
        'steps': route_summary.get('legs', []),
        'logs': logs
    }

    trip = Trip.objects.create(
        current_location=data['current_location'],
        pickup_location=data['pickup_location'],
        dropoff_location=data['dropoff_location'],
        current_cycle_used_hours=data['current_cycle_used_hours'],
        plan_result=out
    )
    return Response({'trip_id': trip.id, 'result': out})

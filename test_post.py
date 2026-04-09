import urllib.request, urllib.error, json
import sys

data = json.dumps({
    'category': 'cheaper', 
    'duration_months': 36, 
    'annual_mileage': 15000, 
    'limit': 2, 
    'requirements': [
        {'feature_key':'opt_paid:Pakiet Winter', 'operator':'eq', 'value':True, 'requirement':'MUST_HAVE'}
    ]
}).encode()

req = urllib.request.Request(
    'http://localhost:8000/api/scoring-search/vehicle/51a611da-b5e9-40bb-8873-ddd156052b04/alternatives', 
    data=data, 
    headers={'Content-Type': 'application/json'}
)

try:
    res = urllib.request.urlopen(req)
    print(res.read().decode())
except urllib.error.HTTPError as e:
    print('ERROR DETAIL:', e.read().decode())
    sys.exit(1)

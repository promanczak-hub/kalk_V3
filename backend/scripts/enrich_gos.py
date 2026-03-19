import sys
import os
import json
from pprint import pprint

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import supabase
from core.feature_cross_reference import rank_catalogs_for_vehicle, cross_reference_vehicle

def main():
    print("Szukam pojazdu GOS-26-059101...")
    resp = supabase.table('vehicle_synthesis').select('id, synthesis_data').execute()
    vehicle_id = None
    
    for r in resp.data:
        synth_str = json.dumps(r.get("synthesis_data", {}))
        if 'GOS-26-059101' in synth_str:
            vehicle_id = r['id']
            break
            
    if not vehicle_id:
        print("Nie znaleziono pojazdu GOS-26-059101.")
        # Fallback to Tavascan
        for r in resp.data:
             if 'Tavascan' in json.dumps(r.get("synthesis_data", {})):
                 vehicle_id = r['id']
                 print(f"Znaleziono innego Tavascana: {vehicle_id}")
                 break
                 
    if not vehicle_id:
        print("Nie znaleziono żadnego Tavascana wpisanego w bazie.")
        return

    print(f"Znaleziono ID pojazdu: {vehicle_id}")

    print("Zbieram dostępne katalogi (Cenniki)...")
    rank_resp = rank_catalogs_for_vehicle(vehicle_id)
    if isinstance(rank_resp, dict) and rank_resp.get("status") == "error":
        print(f"Błąd podczas szukania katalogów: {rank_resp.get('message')}")
        return
        
    if not rank_resp.get("catalog_matches"):
        print("Brak pasujących cenników w bibliotece.")
        return
        
    best_catalog = rank_resp["catalog_matches"][0]
    best_catalog_id = best_catalog["catalog_id"]
    best_catalog_name = best_catalog["catalog_name"]
    print(f"Najlepszy katalog to: {best_catalog_name} ({best_catalog_id}) z wynikiem {best_catalog['score']}")
    
    print("Uruchamiam automatyczne złączenie (merge) cech:")
    res = cross_reference_vehicle(vehicle_id, [best_catalog_id])
    
    print("Wynik cross-reference:")
    pprint(res)
    
if __name__ == "__main__":
    main()

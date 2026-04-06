import asyncio
from core.database import supabase
import pandas as pd

def run():
    res = supabase.table('vehicle_synthesis').select('id, brand, model').eq('model', 'Elroq').execute()
    print('Elroq vehicles:', res.data)
    if res.data:
        for v in res.data:
            vid = v['id']
            print("\nVehicle ID:", vid)
            cache = supabase.table('vehicle_matrix_cache').select('kalkulacja_id, duration_months, annual_mileage, monthly_price_net, calculated_at').eq('vehicle_id', vid).execute()
            print('Cache count:', len(cache.data))
            if cache.data:
                df = pd.DataFrame(cache.data)
                print(df.groupby('kalkulacja_id').size())
                
                # Let's see the latest kalkulacja_id
                latest = df.sort_values('calculated_at', ascending=False).iloc[0]['kalkulacja_id']
                print('Latest kalkulacja_id:', latest)
                latest_rows = df[df['kalkulacja_id'] == latest]
                print("Count of latest rows:", len(latest_rows))
                
                # Check for 60 months, 20k
                match = latest_rows[(latest_rows['duration_months'] == 60) & (latest_rows['annual_mileage'] == 20000)]
                if len(match) > 0:
                    print("60m/20k found:", match.to_dict('records'))
                else:
                    print("60m/20k NOT FOUND for the latest kalkulacja_id!")
                    # Check if it was generated in ANY kalkulacja_id
                    any_match = df[(df['duration_months'] == 60) & (df['annual_mileage'] == 20000)]
                    if len(any_match) > 0:
                        print("BUT it was found in other kalkulacja_id:", any_match['kalkulacja_id'].unique())

if __name__ == '__main__':
    run()

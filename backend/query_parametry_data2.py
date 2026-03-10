import os
from sqlalchemy import create_engine
import pandas as pd

engine = create_engine(os.environ.get("DATABASE_URL"))
query = "SELECT col_1, col_2 FROM \"LTRAdminParametry_czak\" WHERE col_1 IN ('OponyPrzekladki', 'OponyPrzechowywane')"
df = pd.read_sql_query(query, con=engine)
for index, row in df.iterrows():
    print(dict(row))

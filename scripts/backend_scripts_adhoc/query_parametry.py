import os
from sqlalchemy import create_engine
import pandas as pd

engine = create_engine(os.environ.get("DATABASE_URL"))
query = 'SELECT * FROM "LTRAdminParametry_czak" LIMIT 1'
df = pd.read_sql_query(query, con=engine)
print(df.columns.tolist())

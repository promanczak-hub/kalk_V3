from sqlalchemy import create_engine
import pandas as pd

engine = create_engine("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
query = 'SELECT * FROM "LTRAdminParametry_czak" LIMIT 1'
df = pd.read_sql_query(query, con=engine)
print(df.columns.tolist())

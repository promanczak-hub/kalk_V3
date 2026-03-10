import os
import sqlalchemy

url = os.environ.get("DATABASE_URL")
engine = sqlalchemy.create_engine(url)
print(sqlalchemy.inspect(engine).get_table_names())

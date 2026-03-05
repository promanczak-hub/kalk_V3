import sqlalchemy

url = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
engine = sqlalchemy.create_engine(url)
print(sqlalchemy.inspect(engine).get_table_names())

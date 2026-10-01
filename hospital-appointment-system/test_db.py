import psycopg2

connection = psycopg2.connect(
    host="localhost",
    database="hospital_db",
    user="postgres",
    password="kousu2006",
    port="5432"
)

print("Database connected successfully!")

connection.close()
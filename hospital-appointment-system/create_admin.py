from werkzeug.security import generate_password_hash
from app import get_db_connection


# Admin details
name = "Admin"
email = "admin@medicare.com"
password = "admin123"
role = "admin"


# Hash password
hashed_password = generate_password_hash(password)


# Connect to database
connection = get_db_connection()
cursor = connection.cursor()


# Check whether admin already exists
cursor.execute(
    """
    SELECT id
    FROM users
    WHERE email = %s
    """,
    (email,)
)

existing_user = cursor.fetchone()


if existing_user:

    print("Admin already exists.")

else:

    cursor.execute(
        """
        INSERT INTO users
        (name, email, password, role)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (
            name,
            email,
            hashed_password,
            role
        )
    )

    admin_id = cursor.fetchone()[0]

    connection.commit()

    print("Admin created successfully!")
    print("Admin ID:", admin_id)
    print("Email:", email)
    print("Password:", password)


cursor.close()
connection.close()
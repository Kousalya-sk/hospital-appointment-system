from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    connection = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

    return connection


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("home.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:

            # ---------------------------------------------
            # CREATE USER
            # ---------------------------------------------

            cursor.execute(
                """
                INSERT INTO users
                (name, email, password, role)

                VALUES
                (%s, %s, %s, %s)

                RETURNING id
                """,

                (
                    name,
                    email,
                    hashed_password,
                    role
                )
            )

            user_id = cursor.fetchone()[0]


            # ---------------------------------------------
            # CREATE PATIENT PROFILE
            # ---------------------------------------------

            if role == "patient":

                cursor.execute(
                    """
                    INSERT INTO patients
                    (user_id)

                    VALUES
                    (%s)
                    """,

                    (user_id,)
                )


            connection.commit()

            print("===================================")
            print("REGISTERED USER")
            print("USER ID:", user_id)
            print("NAME:", name)
            print("EMAIL:", email)
            print("ROLE:", role)
            print("===================================")

            return redirect(url_for("login"))


        except Exception as error:

            connection.rollback()

            print("REGISTRATION ERROR:", error)

            return f"Registration error: {error}"


        finally:

            cursor.close()
            connection.close()


    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]


        connection = get_db_connection()
        cursor = connection.cursor()


        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password,
                role

            FROM users

            WHERE email = %s
            """,

            (email,)
        )


        user = cursor.fetchone()


        cursor.close()
        connection.close()


        # ---------------------------------------------
        # CHECK USER
        # ---------------------------------------------

        if user:

            if check_password_hash(user[3], password):


                # -----------------------------------------
                # CREATE SESSION
                # -----------------------------------------

                session["user_id"] = user[0]

                session["user_name"] = user[1]

                session["user_role"] = user[4]


                print("===================================")
                print("LOGIN SUCCESS")
                print("USER ID:", user[0])
                print("NAME:", user[1])
                print("ROLE:", user[4])
                print("===================================")


                # -----------------------------------------
                # ADMIN
                # -----------------------------------------

                if user[4] == "admin":

                    return redirect(
                        url_for("admin_dashboard")
                    )


                # -----------------------------------------
                # DOCTOR
                # -----------------------------------------

                elif user[4] == "doctor":

                    return redirect(
                        url_for("doctor_dashboard")
                    )


                # -----------------------------------------
                # PATIENT
                # -----------------------------------------

                else:

                    return redirect(
                        url_for("dashboard")
                    )


        return "Invalid email or password."


    return render_template("login.html")


# =========================================================
# PATIENT DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    # ---------------------------------------------
    # CHECK LOGIN
    # ---------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # ---------------------------------------------
    # PATIENT ONLY
    # ---------------------------------------------

    if session.get("user_role") != "patient":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        user_id = session["user_id"]


        # =============================================
        # GET PATIENT ID
        # =============================================

        cursor.execute(
            """
            SELECT id

            FROM patients

            WHERE user_id = %s
            """,

            (user_id,)
        )


        patient = cursor.fetchone()


        if not patient:

            return "Patient profile not found."


        patient_id = patient[0]


        # =============================================
        # TOTAL APPOINTMENTS
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM appointments

            WHERE patient_id = %s
            """,

            (patient_id,)
        )


        total_appointments = cursor.fetchone()[0]


        # =============================================
        # PENDING APPOINTMENTS
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM appointments

            WHERE patient_id = %s

            AND status = 'Pending'
            """,

            (patient_id,)
        )


        pending_appointments = cursor.fetchone()[0]


        # =============================================
        # COMPLETED APPOINTMENTS
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM appointments

            WHERE patient_id = %s

            AND status = 'Completed'
            """,

            (patient_id,)
        )


        completed_appointments = cursor.fetchone()[0]


        # =============================================
        # TOTAL DOCTORS
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM doctors
            """
        )


        total_doctors = cursor.fetchone()[0]


        # =============================================
        # UPCOMING APPOINTMENT
        #
        # Only Pending and Accepted appointments
        # are displayed.
        # =============================================

        cursor.execute(
            """
            SELECT
                users.name,
                departments.name,
                appointments.appointment_date,
                appointments.appointment_time,
                appointments.reason,
                appointments.status

            FROM appointments

            JOIN doctors
                ON appointments.doctor_id = doctors.id

            JOIN users
                ON doctors.user_id = users.id

            JOIN departments
                ON doctors.department_id = departments.id

            WHERE appointments.patient_id = %s

            AND appointments.appointment_date >= CURRENT_DATE

            AND appointments.status IN
                ('Pending', 'Accepted')

            ORDER BY
                appointments.appointment_date ASC,
                appointments.appointment_time ASC

            LIMIT 1
            """,

            (patient_id,)
        )


        upcoming_appointment = cursor.fetchone()


        # =============================================
        # DISPLAY DASHBOARD
        # =============================================

        return render_template(
            "dashboard.html",

            name=session["user_name"],

            role=session["user_role"],

            total_appointments=total_appointments,

            pending_appointments=pending_appointments,

            completed_appointments=completed_appointments,

            total_doctors=total_doctors,

            upcoming_appointment=upcoming_appointment
        )


    except Exception as error:

        print("===================================")
        print("DASHBOARD ERROR")
        print(error)
        print("===================================")

        return f"Dashboard error: {error}"


    finally:

        cursor.close()
        connection.close()


# =========================================================
# PATIENT PROFILE
# =========================================================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    # ---------------------------------------------
    # LOGIN CHECK
    # ---------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # ---------------------------------------------
    # PATIENT ONLY
    # ---------------------------------------------

    if session.get("user_role") != "patient":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        user_id = session["user_id"]


        # =============================================
        # UPDATE PROFILE
        # =============================================

        if request.method == "POST":

            age = request.form.get("age")
            gender = request.form.get("gender")
            phone = request.form.get("phone")
            address = request.form.get("address")


            print("===================================")
            print("PROFILE UPDATE")
            print("USER ID:", user_id)
            print("AGE:", age)
            print("GENDER:", gender)
            print("PHONE:", phone)
            print("ADDRESS:", address)


            cursor.execute(
                """
                UPDATE patients

                SET
                    age = %s,
                    gender = %s,
                    phone = %s,
                    address = %s

                WHERE user_id = %s
                """,

                (
                    age if age else None,
                    gender if gender else None,
                    phone if phone else None,
                    address if address else None,
                    user_id
                )
            )


            print(
                "ROWS UPDATED:",
                cursor.rowcount
            )


            connection.commit()


            print("PROFILE UPDATE COMMITTED")
            print("===================================")


        # =============================================
        # GET PROFILE
        # =============================================

        cursor.execute(
            """
            SELECT
                users.name,
                users.email,
                patients.age,
                patients.gender,
                patients.phone,
                patients.address

            FROM users

            JOIN patients
                ON users.id = patients.user_id

            WHERE users.id = %s
            """,

            (user_id,)
        )


        patient = cursor.fetchone()


        if not patient:

            return "Patient profile not found."


        return render_template(
            "profile.html",
            patient=patient
        )


    except Exception as error:

        connection.rollback()

        print("PROFILE ERROR:", error)

        return f"Profile error: {error}"


    finally:

        cursor.close()
        connection.close()


# =========================================================
# DOCTORS LIST
# =========================================================

@app.route("/doctors")
def doctors():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        cursor.execute(
            """
            SELECT
                doctors.id,
                users.name,
                departments.name,
                doctors.specialization,
                doctors.experience,
                doctors.phone

            FROM doctors

            JOIN users
                ON doctors.user_id = users.id

            JOIN departments
                ON doctors.department_id = departments.id

            ORDER BY doctors.id
            """
        )


        doctors_list = cursor.fetchall()


        return render_template(
            "doctors.html",
            doctors=doctors_list
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# BOOK APPOINTMENT
# =========================================================

@app.route(
    "/book-appointment/<int:doctor_id>",
    methods=["GET", "POST"]
)
def book_appointment(doctor_id):

    # ---------------------------------------------
    # LOGIN CHECK
    # ---------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # ---------------------------------------------
    # PATIENT ONLY
    # ---------------------------------------------

    if session.get("user_role") != "patient":

        return "Only patients can book appointments."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        # =============================================
        # GET PATIENT
        # =============================================

        cursor.execute(
            """
            SELECT id

            FROM patients

            WHERE user_id = %s
            """,

            (session["user_id"],)
        )


        patient = cursor.fetchone()


        if not patient:

            return "Patient profile not found."


        patient_id = patient[0]


        # =============================================
        # BOOK APPOINTMENT
        # =============================================

        if request.method == "POST":

            appointment_date = request.form[
                "appointment_date"
            ]

            appointment_time = request.form[
                "appointment_time"
            ]

            reason = request.form[
                "reason"
            ]


            # -----------------------------------------
            # CHECK DOUBLE BOOKING
            # -----------------------------------------

            cursor.execute(
                """
                SELECT id

                FROM appointments

                WHERE doctor_id = %s

                AND appointment_date = %s

                AND appointment_time = %s

                AND status IN
                    ('Pending', 'Accepted')
                """,

                (
                    doctor_id,
                    appointment_date,
                    appointment_time
                )
            )


            existing = cursor.fetchone()


            if existing:

                return (
                    "This appointment slot is "
                    "already booked. Please select "
                    "another time."
                )


            # -----------------------------------------
            # INSERT APPOINTMENT
            # -----------------------------------------

            cursor.execute(
                """
                INSERT INTO appointments
                (
                    patient_id,
                    doctor_id,
                    appointment_date,
                    appointment_time,
                    reason,
                    status
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,

                (
                    patient_id,
                    doctor_id,
                    appointment_date,
                    appointment_time,
                    reason,
                    "Pending"
                )
            )


            connection.commit()


            return redirect(
                url_for("my_appointments")
            )


        # =============================================
        # GET DOCTOR DETAILS
        # =============================================

        cursor.execute(
            """
            SELECT
                users.name,
                departments.name,
                doctors.specialization

            FROM doctors

            JOIN users
                ON doctors.user_id = users.id

            JOIN departments
                ON doctors.department_id =
                   departments.id

            WHERE doctors.id = %s
            """,

            (doctor_id,)
        )


        doctor = cursor.fetchone()


        if not doctor:

            return "Doctor not found."


        return render_template(
            "book_appointment.html",

            doctor=doctor,

            doctor_id=doctor_id
        )


    except Exception as error:

        connection.rollback()

        return f"Booking error: {error}"


    finally:

        cursor.close()
        connection.close()


# =========================================================
# PATIENT APPOINTMENTS
# =========================================================

@app.route("/my-appointments")
def my_appointments():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "patient":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        cursor.execute(
            """
            SELECT
                appointments.id,
                users.name,
                departments.name,
                doctors.specialization,
                appointments.appointment_date,
                appointments.appointment_time,
                appointments.reason,
                appointments.status

            FROM appointments

            JOIN doctors
                ON appointments.doctor_id = doctors.id

            JOIN users
                ON doctors.user_id = users.id

            JOIN departments
                ON doctors.department_id =
                   departments.id

            JOIN patients
                ON appointments.patient_id =
                   patients.id

            WHERE patients.user_id = %s

            ORDER BY
                appointments.appointment_date,
                appointments.appointment_time
            """,

            (session["user_id"],)
        )


        appointments = cursor.fetchall()


        return render_template(
            "my_appointments.html",
            appointments=appointments
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# CANCEL APPOINTMENT
# =========================================================

@app.route(
    "/cancel-appointment/<int:appointment_id>"
)
def cancel_appointment(appointment_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "patient":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        cursor.execute(
            """
            UPDATE appointments

            SET status = 'Cancelled'

            WHERE id = %s

            AND patient_id = (
                SELECT id

                FROM patients

                WHERE user_id = %s
            )

            AND status IN
                ('Pending', 'Accepted')
            """,

            (
                appointment_id,
                session["user_id"]
            )
        )


        connection.commit()


        return redirect(
            url_for("my_appointments")
        )


    except Exception as error:

        connection.rollback()

        return f"Cancellation error: {error}"


    finally:

        cursor.close()
        connection.close()


# =========================================================
# DOCTOR DASHBOARD
# =========================================================

@app.route("/doctor-dashboard")
def doctor_dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "doctor":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        doctor_user_id = session["user_id"]


        # =============================================
        # GET DOCTOR ID
        # =============================================

        cursor.execute(
            """
            SELECT id

            FROM doctors

            WHERE user_id = %s
            """,

            (doctor_user_id,)
        )


        doctor = cursor.fetchone()


        if not doctor:

            return "Doctor profile not found."


        doctor_id = doctor[0]


        # =============================================
        # TOTAL APPOINTMENTS
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM appointments

            WHERE doctor_id = %s
            """,

            (doctor_id,)
        )


        total_appointments = cursor.fetchone()[0]


        # =============================================
        # PENDING
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM appointments

            WHERE doctor_id = %s

            AND status = 'Pending'
            """,

            (doctor_id,)
        )


        pending_appointments = cursor.fetchone()[0]


        # =============================================
        # ACCEPTED
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM appointments

            WHERE doctor_id = %s

            AND status = 'Accepted'
            """,

            (doctor_id,)
        )


        accepted_appointments = cursor.fetchone()[0]


        # =============================================
        # COMPLETED
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM appointments

            WHERE doctor_id = %s

            AND status = 'Completed'
            """,

            (doctor_id,)
        )


        completed_appointments = cursor.fetchone()[0]


        return render_template(
            "doctor_dashboard.html",

            name=session["user_name"],

            total_appointments=
                total_appointments,

            pending_appointments=
                pending_appointments,

            accepted_appointments=
                accepted_appointments,

            completed_appointments=
                completed_appointments
        )


    except Exception as error:

        return f"Doctor dashboard error: {error}"


    finally:

        cursor.close()
        connection.close()


# =========================================================
# DOCTOR APPOINTMENTS
# =========================================================

@app.route("/doctor-appointments")
def doctor_appointments():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "doctor":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        cursor.execute(
            """
            SELECT
                appointments.id,
                users.name,
                appointments.appointment_date,
                appointments.appointment_time,
                appointments.reason,
                appointments.status

            FROM appointments

            JOIN patients
                ON appointments.patient_id =
                   patients.id

            JOIN users
                ON patients.user_id =
                   users.id

            JOIN doctors
                ON appointments.doctor_id =
                   doctors.id

            WHERE doctors.user_id = %s

            ORDER BY
                appointments.appointment_date,
                appointments.appointment_time
            """,

            (session["user_id"],)
        )


        appointments = cursor.fetchall()


        return render_template(
            "doctor_appointments.html",

            appointments=appointments
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# DOCTOR UPDATE APPOINTMENT STATUS
# =========================================================

@app.route(
    "/update-appointment/<int:appointment_id>",
    methods=["POST"]
)
def update_appointment(appointment_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "doctor":

        return "Access denied."


    status = request.form["status"]


    # ---------------------------------------------
    # ALLOWED STATUS VALUES
    # ---------------------------------------------

    allowed_statuses = [
        "Pending",
        "Accepted",
        "Rejected",
        "Completed",
        "Cancelled"
    ]


    if status not in allowed_statuses:

        return "Invalid appointment status."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        cursor.execute(
            """
            UPDATE appointments

            SET status = %s

            WHERE id = %s

            AND doctor_id = (
                SELECT id

                FROM doctors

                WHERE user_id = %s
            )
            """,

            (
                status,
                appointment_id,
                session["user_id"]
            )
        )


        connection.commit()


        return redirect(
            url_for("doctor_appointments")
        )


    except Exception as error:

        connection.rollback()

        return f"Status update error: {error}"


    finally:

        cursor.close()
        connection.close()


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin-dashboard")
def admin_dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "admin":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        # =============================================
        # TOTAL PATIENTS
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM patients
            """
        )

        total_patients = cursor.fetchone()[0]


        # =============================================
        # TOTAL DOCTORS
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM doctors
            """
        )

        total_doctors = cursor.fetchone()[0]


        # =============================================
        # TOTAL APPOINTMENTS
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM appointments
            """
        )

        total_appointments = cursor.fetchone()[0]


        # =============================================
        # PENDING APPOINTMENTS
        # =============================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM appointments

            WHERE status = 'Pending'
            """
        )

        pending_appointments = cursor.fetchone()[0]


        return render_template(
            "admin_dashboard.html",

            total_patients=total_patients,

            total_doctors=total_doctors,

            total_appointments=
                total_appointments,

            pending_appointments=
                pending_appointments
        )


    except Exception as error:

        return f"Admin dashboard error: {error}"


    finally:

        cursor.close()
        connection.close()


# =========================================================
# ADMIN DEPARTMENTS
# =========================================================

@app.route(
    "/admin-departments",
    methods=["GET", "POST"]
)
def admin_departments():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "admin":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        # =============================================
        # ADD DEPARTMENT
        # =============================================

        if request.method == "POST":

            name = request.form["name"]


            try:

                cursor.execute(
                    """
                    INSERT INTO departments
                    (name)

                    VALUES
                    (%s)
                    """,

                    (name,)
                )


                connection.commit()


            except Exception as error:

                connection.rollback()

                return (
                    f"Error adding department: "
                    f"{error}"
                )


        # =============================================
        # GET DEPARTMENTS
        # =============================================

        cursor.execute(
            """
            SELECT
                id,
                name

            FROM departments

            ORDER BY id
            """
        )


        departments = cursor.fetchall()


        return render_template(
            "admin_departments.html",

            departments=departments
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# DELETE DEPARTMENT
# =========================================================

@app.route(
    "/delete-department/<int:department_id>"
)
def delete_department(department_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "admin":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        cursor.execute(
            """
            DELETE FROM departments

            WHERE id = %s
            """,

            (department_id,)
        )


        connection.commit()


        return redirect(
            url_for("admin_departments")
        )


    except Exception as error:

        connection.rollback()

        return (
            "Error deleting department. "
            "It may be connected to existing doctors."
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# ADMIN DOCTORS
# =========================================================

@app.route(
    "/admin-doctors",
    methods=["GET", "POST"]
)
def admin_doctors():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "admin":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        # =============================================
        # ADD DOCTOR
        # =============================================

        if request.method == "POST":

            name = request.form["name"]

            email = request.form["email"]

            password = request.form["password"]

            department_id = request.form[
                "department_id"
            ]

            specialization = request.form[
                "specialization"
            ]

            experience = request.form[
                "experience"
            ]

            phone = request.form["phone"]


            hashed_password = \
                generate_password_hash(password)


            try:

                # -------------------------------------
                # CREATE USER
                # -------------------------------------

                cursor.execute(
                    """
                    INSERT INTO users
                    (
                        name,
                        email,
                        password,
                        role
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s
                    )

                    RETURNING id
                    """,

                    (
                        name,
                        email,
                        hashed_password,
                        "doctor"
                    )
                )


                user_id = cursor.fetchone()[0]


                # -------------------------------------
                # CREATE DOCTOR
                # -------------------------------------

                cursor.execute(
                    """
                    INSERT INTO doctors
                    (
                        user_id,
                        department_id,
                        specialization,
                        experience,
                        phone
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,

                    (
                        user_id,
                        department_id,
                        specialization,
                        experience,
                        phone
                    )
                )


                connection.commit()


            except Exception as error:

                connection.rollback()

                return (
                    f"Error adding doctor: "
                    f"{error}"
                )


        # =============================================
        # GET DOCTORS
        # =============================================

        cursor.execute(
            """
            SELECT
                doctors.id,
                users.name,
                users.email,
                departments.name,
                doctors.specialization,
                doctors.experience,
                doctors.phone

            FROM doctors

            JOIN users
                ON doctors.user_id = users.id

            JOIN departments
                ON doctors.department_id =
                   departments.id

            ORDER BY doctors.id
            """
        )


        doctors_list = cursor.fetchall()


        # =============================================
        # GET DEPARTMENTS
        # =============================================

        cursor.execute(
            """
            SELECT
                id,
                name

            FROM departments

            ORDER BY id
            """
        )


        departments = cursor.fetchall()


        return render_template(
            "admin_doctors.html",

            doctors=doctors_list,

            departments=departments
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# DELETE DOCTOR
# =========================================================

@app.route(
    "/delete-doctor/<int:doctor_id>"
)
def delete_doctor(doctor_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "admin":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        # =============================================
        # GET USER ID
        # =============================================

        cursor.execute(
            """
            SELECT user_id

            FROM doctors

            WHERE id = %s
            """,

            (doctor_id,)
        )


        doctor = cursor.fetchone()


        if doctor:

            user_id = doctor[0]


            # -----------------------------------------
            # DELETE DOCTOR
            # -----------------------------------------

            cursor.execute(
                """
                DELETE FROM doctors

                WHERE id = %s
                """,

                (doctor_id,)
            )


            # -----------------------------------------
            # DELETE USER
            # -----------------------------------------

            cursor.execute(
                """
                DELETE FROM users

                WHERE id = %s
                """,

                (user_id,)
            )


            connection.commit()


        return redirect(
            url_for("admin_doctors")
        )


    except Exception as error:

        connection.rollback()

        return (
            "Error deleting doctor. "
            "The doctor may have appointments."
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# ADMIN PATIENTS
# =========================================================

@app.route("/admin-patients")
def admin_patients():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "admin":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        cursor.execute(
            """
            SELECT
                patients.id,
                users.name,
                users.email,
                patients.age,
                patients.gender,
                patients.phone,
                patients.address

            FROM patients

            JOIN users
                ON patients.user_id = users.id

            ORDER BY patients.id
            """
        )


        patients = cursor.fetchall()


        return render_template(
            "admin_patients.html",

            patients=patients
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# DELETE PATIENT
# =========================================================

@app.route(
    "/delete-patient/<int:patient_id>"
)
def delete_patient(patient_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "admin":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        # =============================================
        # GET USER ID
        # =============================================

        cursor.execute(
            """
            SELECT user_id

            FROM patients

            WHERE id = %s
            """,

            (patient_id,)
        )


        patient = cursor.fetchone()


        if patient:

            user_id = patient[0]


            # -----------------------------------------
            # DELETE PATIENT
            # -----------------------------------------

            cursor.execute(
                """
                DELETE FROM patients

                WHERE id = %s
                """,

                (patient_id,)
            )


            # -----------------------------------------
            # DELETE USER
            # -----------------------------------------

            cursor.execute(
                """
                DELETE FROM users

                WHERE id = %s
                """,

                (user_id,)
            )


            connection.commit()


        return redirect(
            url_for("admin_patients")
        )


    except Exception as error:

        connection.rollback()

        return (
            "Error deleting patient. "
            "The patient may have appointments."
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# ADMIN APPOINTMENTS
# =========================================================

@app.route("/admin-appointments")
def admin_appointments():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "admin":

        return "Access denied."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        cursor.execute(
            """
            SELECT
                appointments.id,

                patient_users.name,

                doctor_users.name,

                departments.name,

                appointments.appointment_date,

                appointments.appointment_time,

                appointments.reason,

                appointments.status

            FROM appointments

            JOIN patients
                ON appointments.patient_id =
                   patients.id

            JOIN users AS patient_users
                ON patients.user_id =
                   patient_users.id

            JOIN doctors
                ON appointments.doctor_id =
                   doctors.id

            JOIN users AS doctor_users
                ON doctors.user_id =
                   doctor_users.id

            JOIN departments
                ON doctors.department_id =
                   departments.id

            ORDER BY
                appointments.appointment_date DESC,

                appointments.appointment_time DESC
            """
        )


        appointments = cursor.fetchall()


        return render_template(
            "admin_appointments.html",

            appointments=appointments
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# ADMIN UPDATE APPOINTMENT STATUS
# =========================================================

@app.route(
    "/admin-update-appointment/<int:appointment_id>",
    methods=["POST"]
)
def admin_update_appointment(appointment_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("user_role") != "admin":

        return "Access denied."


    status = request.form["status"]


    allowed_statuses = [
        "Pending",
        "Accepted",
        "Rejected",
        "Completed",
        "Cancelled"
    ]


    if status not in allowed_statuses:

        return "Invalid status."


    connection = get_db_connection()
    cursor = connection.cursor()


    try:

        cursor.execute(
            """
            UPDATE appointments

            SET status = %s

            WHERE id = %s
            """,

            (
                status,
                appointment_id
            )
        )


        connection.commit()


        return redirect(
            url_for("admin_appointments")
        )


    except Exception as error:

        connection.rollback()

        return (
            f"Appointment update error: "
            f"{error}"
        )


    finally:

        cursor.close()
        connection.close()


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash,generate_password_hash
import mysql.connector
from datetime import datetime, timedelta
import re
import secrets
import string

app = Flask(__name__)

import os
from dotenv import load_dotenv

load_dotenv()

app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")
# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        port=int(os.environ.get("DB_PORT", 3306))
    )# =========================================================
# TIME FORMATTER
# =========================================================

def format_time(time_value):

    if time_value is None:
        return ""

    # MySQL TIME can sometimes come as timedelta
    if isinstance(time_value, timedelta):

        total_seconds = int(time_value.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        period = "AM"

        if hours >= 12:
            period = "PM"

        display_hour = hours

        if hours > 12:
            display_hour = hours - 12

        if hours == 0:
            display_hour = 12

        return f"{display_hour:02d}:{minutes:02d} {period}"

    # datetime.time
    if hasattr(time_value, "strftime"):
        return time_value.strftime("%I:%M %p")

    return str(time_value)


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM hospitals
        LIMIT 1
    """)

    hospital = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        "index.html",
        hospital=hospital
    )


# =========================================================
# DOCTORS LIST
# =========================================================

@app.route("/doctors")
def doctors():

    specialization = request.args.get("specialization")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if specialization:

        query = """
            SELECT
                doctors.id,
                users.name,
                doctors.specialization,
                doctors.qualification,
                doctors.experience,
                doctors.consultation_fee,
                doctors.bio
            FROM doctors
            JOIN users
                ON doctors.user_id = users.id
            WHERE doctors.specialization = %s
            ORDER BY users.name
        """

        cursor.execute(
            query,
            (specialization,)
        )

    else:

        query = """
            SELECT
                doctors.id,
                users.name,
                doctors.specialization,
                doctors.qualification,
                doctors.experience,
                doctors.consultation_fee,
                doctors.bio
            FROM doctors
            JOIN users
                ON doctors.user_id = users.id
            ORDER BY users.name
        """

        cursor.execute(query)

    doctors = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "doctors.html",
        doctors=doctors,
        specialization=specialization
    )

# =========================================================
# DOCTOR PROFILE
# =========================================================

@app.route("/doctors/<int:doctor_id>")
def doctor_profile(doctor_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    doctor_query = """
        SELECT
            doctors.id,
            users.name,
            doctors.specialization,
            doctors.qualification,
            doctors.experience,
            doctors.consultation_fee,
            doctors.bio
        FROM doctors
        JOIN users
            ON doctors.user_id = users.id
        WHERE doctors.id = %s
    """

    cursor.execute(
        doctor_query,
        (doctor_id,)
    )

    doctor = cursor.fetchone()

    if doctor is None:

        cursor.close()
        connection.close()

        return "Doctor not found", 404

    availability_query = """
        SELECT
            day_of_week,
            start_time,
            end_time
        FROM doctor_availability
        WHERE doctor_id = %s
        ORDER BY
            FIELD(
                day_of_week,
                'Monday',
                'Tuesday',
                'Wednesday',
                'Thursday',
                'Friday',
                'Saturday',
                'Sunday'
            )
    """

    cursor.execute(
        availability_query,
        (doctor_id,)
    )

    availability = cursor.fetchall()

    # Format times
    for slot in availability:

        slot["start_time"] = format_time(
            slot["start_time"]
        )

        slot["end_time"] = format_time(
            slot["end_time"]
        )

    cursor.close()
    connection.close()

    return render_template(
        "doctor_profile.html",
        doctor=doctor,
        availability=availability
    )


# =========================================================
# BOOK APPOINTMENT
# =========================================================
@app.route(
    "/doctors/<int:doctor_id>/book",
    methods=["GET", "POST"]
)
def book_appointment(doctor_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # =====================================================
    # GET DOCTOR
    # =====================================================

    cursor.execute(
        """
        SELECT
            doctors.id,
            doctors.hospital_id,
            users.name,
            doctors.specialization,
            doctors.qualification,
            doctors.consultation_fee
        FROM doctors
        JOIN users
            ON doctors.user_id = users.id
        WHERE doctors.id = %s
        """,
        (doctor_id,)
    )

    doctor = cursor.fetchone()

    if doctor is None:

        cursor.close()
        connection.close()

        return "Doctor not found", 404


    # =====================================================
    # POST - BOOK APPOINTMENT
    # =====================================================

    if request.method == "POST":

        patient_name = request.form.get(
            "patient_name",
            ""
        ).strip()

        patient_phone = request.form.get(
            "patient_phone",
            ""
        ).strip()


        appointment_date = request.form.get(
            "appointment_date"
        )

        appointment_time = request.form.get(
            "appointment_time"
        )

        consultation_type = request.form.get(
            "consultation_type"
        )

        reason = request.form.get(
            "reason",
            ""
        ).strip()


        # =================================================
        # VALIDATION
        # =================================================

        if not patient_name:
            cursor.close()
            connection.close()
            return "Please enter patient name.", 400

        if not patient_phone:
            cursor.close()
            connection.close()
            return "Please enter phone number.", 400

        

        if not re.fullmatch(r"[0-9+()\- ]{7,20}", patient_phone):
            cursor.close()
            connection.close()
            return "Please enter a valid phone number.", 400

        if not appointment_date:
            cursor.close()
            connection.close()
            return "Please select appointment date.", 400

        try:
            selected_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        except ValueError:
            cursor.close()
            connection.close()
            return "Invalid appointment date.", 400

        if selected_date < datetime.now().date():
            cursor.close()
            connection.close()
            return "Appointment date cannot be in the past.", 400

        if not appointment_time:
            cursor.close()
            connection.close()
            return "Please select appointment time.", 400

        if not consultation_type:
            cursor.close()
            connection.close()
            return "Please select consultation type.", 400


        # =================================================
        # FIND PATIENT USER
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone
            FROM users
            WHERE phone = %s
            AND role = 'patient'
            LIMIT 1
            """,
            (patient_phone,)
        )

        user = cursor.fetchone()


        # =================================================
        # EXISTING USER
        # =================================================

        if user:

            user_id = user["id"]

            # Check patients table

            cursor.execute(
                """
                SELECT id
                FROM patients
                WHERE user_id = %s
                LIMIT 1
                """,
                (user_id,)
            )

            patient = cursor.fetchone()


            if patient:

                patient_id = patient["id"]

            else:

                # User exists but patient record doesn't

                cursor.execute(
                    """
                    INSERT INTO patients
                    (
                        user_id
                    )
                    VALUES
                    (%s)
                    """,
                    (user_id,)
                )

                patient_id = cursor.lastrowid


        # =================================================
        # NEW PATIENT
        # =================================================

        else:

            # Create password hash.
            # Patient doesn't need to login currently,
            # but we still store a proper password hash.

            password_hash = generate_password_hash(
                patient_phone
            )


                        # Create an internal email because the database
            # still requires the email column.
            patient_internal_email = (
                f"patient_{patient_phone}@padmahospital.local"
            )

            cursor.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    phone,
                    password_hash,
                    role
                )
                VALUES
                (%s, %s, %s, %s, %s)
                """,
                (
                    patient_name,
                    patient_internal_email,
                    patient_phone,
                    password_hash,
                    "patient"
                )
            )

            user_id = cursor.lastrowid


            # Create patient record

            cursor.execute(
                """
                INSERT INTO patients
                (
                    user_id
                )
                VALUES
                (%s)
                """,
                (user_id,)
            )

            patient_id = cursor.lastrowid


        # =================================================
        # CHECK EXISTING TIME SLOT
        # =================================================

        cursor.execute(
            """
            SELECT id
            FROM appointments
            WHERE doctor_id = %s
            AND appointment_date = %s
            AND appointment_time = %s
            AND status != 'cancelled'
            LIMIT 1
            """,
            (
                doctor_id,
                appointment_date,
                appointment_time
            )
        )

        existing = cursor.fetchone()


        if existing:

            # Get availability again

            cursor.execute(
                """
                SELECT
                    day_of_week,
                    start_time,
                    end_time
                FROM doctor_availability
                WHERE doctor_id = %s
                ORDER BY FIELD(
                    day_of_week,
                    'Monday',
                    'Tuesday',
                    'Wednesday',
                    'Thursday',
                    'Friday',
                    'Saturday',
                    'Sunday'
                )
                """,
                (doctor_id,)
            )

            availability = cursor.fetchall()


            for item in availability:

                item["start_display"] = format_time(
                    item["start_time"]
                )

                item["end_display"] = format_time(
                    item["end_time"]
                )


            connection.rollback()

            cursor.close()
            connection.close()


            return render_template(
                "book_appointment.html",
                doctor=doctor,
                availability=availability,
                error=(
                    "This time slot has already been booked. "
                    "Please select another time."
                )
            )


        # =================================================
        # INSERT APPOINTMENT
        # =================================================

        cursor.execute(
            """
            INSERT INTO appointments
            (
                patient_id,
                doctor_id,
                hospital_id,
                appointment_date,
                appointment_time,
                consultation_type,
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
                %s,
                %s,
                %s
            )
            """,
            (
                patient_id,
                doctor_id,
                doctor["hospital_id"],
                appointment_date,
                appointment_time,
                consultation_type,
                reason,
                "confirmed"
            )
        )


        # =================================================
        # GET APPOINTMENT ID
        # =================================================

        appointment_id = cursor.lastrowid


        # =================================================
        # GENERATE TOKEN
        # =================================================

        characters = string.ascii_uppercase + string.digits

        random_token = ''.join(
            secrets.choice(characters)
                for _ in range(6)
        )

        token_number = f"PAD-{random_token}"


        # =================================================
        # SAVE TOKEN
        # =================================================

        cursor.execute(
            """
            UPDATE appointments
            SET token_number = %s
            WHERE id = %s
            """,
            (
                token_number,
                appointment_id
            )
        )


        # =================================================
        # COMMIT
        # =================================================

        connection.commit()


        cursor.close()
        connection.close()


        # =================================================
        # SUCCESS PAGE
        # =================================================

        return render_template(
            "booking_success.html",
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            token_number=token_number,
            patient_name=patient_name,
            patient_phone=patient_phone
        )


    # =====================================================
    # GET - BOOKING PAGE
    # =====================================================

    cursor.execute(
        """
        SELECT
            day_of_week,
            start_time,
            end_time
        FROM doctor_availability
        WHERE doctor_id = %s
        ORDER BY FIELD(
            day_of_week,
            'Monday',
            'Tuesday',
            'Wednesday',
            'Thursday',
            'Friday',
            'Saturday',
            'Sunday'
        )
        """,
        (doctor_id,)
    )

    availability = cursor.fetchall()


    # =====================================================
    # FORMAT AVAILABILITY
    # =====================================================

    for item in availability:

        item["start_display"] = format_time(
            item["start_time"]
        )

        item["end_display"] = format_time(
            item["end_time"]
        )


    cursor.close()
    connection.close()


    return render_template(
        "book_appointment.html",
        doctor=doctor,
        availability=availability
    )
# =========================================================
# API - AVAILABLE TIME SLOTS
# =========================================================

@app.route(
    "/api/doctors/<int:doctor_id>/availability"
)
def get_available_slots(doctor_id):

    appointment_date = request.args.get("date")

    if not appointment_date:

        return {
            "error": "Date is required"
        }, 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # -------------------------------------------------
        # GET DAY NAME
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT DAYNAME(%s) AS day_name
            """,
            (appointment_date,)
        )

        result = cursor.fetchone()

        if not result:

            return {
                "available": False,
                "slots": []
            }

        day_name = result["day_name"]

        # -------------------------------------------------
        # GET WORKING HOURS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                start_time,
                end_time
            FROM doctor_availability
            WHERE doctor_id = %s
            AND day_of_week = %s
            """,
            (
                doctor_id,
                day_name
            )
        )

        availability = cursor.fetchone()

        if availability is None:

            return {
                "available": False,
                "day": day_name,
                "message": "Doctor is not available on this day.",
                "slots": []
            }

        # -------------------------------------------------
        # GET BOOKED TIMES
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT appointment_time
            FROM appointments
            WHERE doctor_id = %s
            AND appointment_date = %s
            AND status != 'cancelled'
            """,
            (
                doctor_id,
                appointment_date
            )
        )

        booked = cursor.fetchall()

        booked_times = set()

        for row in booked:

            appointment_time = row["appointment_time"]

            if appointment_time is None:
                continue

            if isinstance(
                appointment_time,
                timedelta
            ):

                total_seconds = int(
                    appointment_time.total_seconds()
                )

                hours = total_seconds // 3600

                minutes = (
                    total_seconds % 3600
                ) // 60

                seconds = (
                    total_seconds % 60
                )

                booked_times.add(
                    f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                )

            else:

                booked_times.add(
                    str(appointment_time)
                )

        # -------------------------------------------------
        # CONVERT TIME TO MINUTES
        # -------------------------------------------------

        def time_to_minutes(value):

            if isinstance(value, timedelta):

                return int(
                    value.total_seconds() // 60
                )

            if hasattr(value, "hour"):

                return (
                    value.hour * 60
                    + value.minute
                )

            return 0

        start_minutes = time_to_minutes(
            availability["start_time"]
        )

        end_minutes = time_to_minutes(
            availability["end_time"]
        )

        # -------------------------------------------------
        # GENERATE 30 MINUTE SLOTS
        # -------------------------------------------------

        slots = []

        current_minutes = start_minutes

        while current_minutes < end_minutes:

            hours = current_minutes // 60

            minutes = current_minutes % 60

            time_string = (
                f"{hours:02d}:{minutes:02d}:00"
            )

            # 12-hour format
            display_hour = hours

            period = "AM"

            if hours >= 12:
                period = "PM"

            if hours > 12:
                display_hour = hours - 12

            if hours == 0:
                display_hour = 12

            display_time = (
                f"{display_hour:02d}:"
                f"{minutes:02d} "
                f"{period}"
            )

            # Only free slots
            if time_string not in booked_times:

                slots.append({
                    "value": time_string,
                    "display": display_time
                })

            current_minutes += 30

        return {
            "available": True,
            "day": day_name,
            "slots": slots
        }

    finally:

        cursor.close()
        connection.close()

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                password_hash,
                role
            FROM users
            WHERE email = %s
            AND role = 'doctor'
            """,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()


        # User doesn't exist

        if user is None:

            return render_template(
                "login.html",
                error="Invalid email or password."
            )


        # Check password

        if not check_password_hash(
                user["password_hash"],
                            password
                                ):

            return render_template(
        "login.html",
        error="Invalid email or password."
    )


        # Login successful

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]


        # Redirect based on role

        if user["role"] == "patient":

            return redirect(url_for("patient_dashboard"))


        elif user["role"] == "doctor":

            return redirect(url_for("doctor_dashboard"))


        elif user["role"] == "hospital_admin":

            return redirect(url_for("admin_dashboard"))


        else:

            return render_template(
                "login.html",
                error="Invalid user role."
            )

    return render_template("login.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

@app.route("/patient/dashboard")
def patient_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "patient_dashboard.html",
        user_name=session["user_name"]
    )
@app.route("/doctor/dashboard")
def doctor_dashboard():

    # ---------------------------------------------
    # CHECK LOGIN
    # ---------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Make sure logged-in user is a doctor
    if session.get("user_role") != "doctor":
        return "Access denied", 403


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # ---------------------------------------------
    # GET DOCTOR ID
    # ---------------------------------------------

    cursor.execute(
        """
        SELECT id
        FROM doctors
        WHERE user_id = %s
        """,
        (session["user_id"],)
    )

    doctor = cursor.fetchone()


    if doctor is None:

        cursor.close()
        connection.close()

        return "Doctor profile not found", 404


    doctor_id = doctor["id"]


    # ---------------------------------------------
    # GET APPOINTMENTS
    # ---------------------------------------------

    cursor.execute(
            """
            SELECT
                appointments.id,
                appointments.token_number,
                appointments.appointment_date,
                appointments.appointment_time,
                appointments.consultation_type,
                appointments.reason,
                appointments.status,

                patients.id AS patient_id,
                users.name AS patient_name,
                users.phone AS patient_phone,

                doctors.id AS doctor_id,
                doctor_users.name AS doctor_name,
                doctors.specialization

            FROM appointments

            JOIN patients
                ON appointments.patient_id = patients.id

            JOIN users
                ON patients.user_id = users.id

            JOIN doctors
                ON appointments.doctor_id = doctors.id

            JOIN users AS doctor_users
                ON doctors.user_id = doctor_users.id

            WHERE appointments.doctor_id = %s
            AND appointments.status != 'completed'
            AND appointments.status != 'cancelled'

            ORDER BY
                appointments.appointment_date ASC,
                appointments.appointment_time ASC
            """,
            (doctor_id,)
        )

    appointments = cursor.fetchall()
    


    cursor.close()
    connection.close()


    return render_template(
        "doctor_dashboard.html",
        user_name=session["user_name"],
        appointments=appointments
    )
@app.route("/doctor/appointment/<int:appointment_id>/verify")
def verify_appointment(appointment_id):

    # ---------------------------------------------
    # CHECK LOGIN
    # ---------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Only doctors can verify appointments
    if session.get("user_role") != "doctor":
        return "Access denied", 403


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # ---------------------------------------------
    # GET DOCTOR
    # ---------------------------------------------

    cursor.execute(
        """
        SELECT id
        FROM doctors
        WHERE user_id = %s
        """,
        (session["user_id"],)
    )

    doctor = cursor.fetchone()


    if doctor is None:

        cursor.close()
        connection.close()

        return "Doctor profile not found", 404


    # ---------------------------------------------
    # GET APPOINTMENT
    # ---------------------------------------------

    cursor.execute(
    """
    SELECT
        appointments.id,
        appointments.token_number,
        appointments.appointment_date,
        appointments.appointment_time,
        appointments.consultation_type,
        appointments.reason,
        appointments.status,

        patient_users.name AS patient_name,
        patient_users.phone AS patient_phone,
        patient_users.email AS patient_email

    FROM appointments

    JOIN patients
        ON appointments.patient_id = patients.id

    JOIN users AS patient_users
        ON patients.user_id = patient_users.id

    WHERE appointments.id = %s
    AND appointments.doctor_id = %s
    """,
    (
        appointment_id,
        doctor["id"]
    )
)

    appointment = cursor.fetchone()


    cursor.close()
    connection.close()


    if appointment is None:

        return "Appointment not found", 404


    return render_template(
        "verify_appointment.html",
        appointment=appointment
    )
@app.route(
    "/doctor/appointment/<int:appointment_id>/complete",
    methods=["POST"]
)
def complete_appointment(appointment_id):

    # ---------------------------------------------
    # CHECK LOGIN
    # ---------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Only doctors can complete appointments
    if session.get("user_role") != "doctor":
        return "Access denied", 403


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    try:

        # ---------------------------------------------
        # GET DOCTOR ID
        # ---------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM doctors
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()


        if doctor is None:

            return "Doctor profile not found", 404


        doctor_id = doctor["id"]


        # ---------------------------------------------
        # CHECK APPOINTMENT BELONGS TO THIS DOCTOR
        # ---------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM appointments
            WHERE id = %s
            AND doctor_id = %s
            """,
            (
                appointment_id,
                doctor_id
            )
        )

        appointment = cursor.fetchone()


        if appointment is None:

            return "Appointment not found", 404


        # ---------------------------------------------
        # MARK APPOINTMENT AS COMPLETED
        # ---------------------------------------------

        cursor.execute(
            """
            UPDATE appointments
            SET status = 'completed'
            WHERE id = %s
            AND doctor_id = %s
            """,
            (
                appointment_id,
                doctor_id
            )
        )


        connection.commit()


        # ---------------------------------------------
        # RETURN TO DOCTOR DASHBOARD
        # ---------------------------------------------

        return redirect(
            url_for("doctor_dashboard")
        )


    except Exception:

        connection.rollback()
        raise


    finally:

        cursor.close()
        connection.close()

@app.route("/appointments", methods=["GET", "POST"])
def appointments():

    if request.method == "POST":

        phone = request.form.get("phone", "").strip()

        if not phone:
            return render_template(
                "appointments.html",
                appointments=[],
                error="Please enter your phone number.",
                phone=""
            )

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                appointments.id,
                appointments.token_number,
                appointments.appointment_date,
                appointments.appointment_time,
                appointments.consultation_type,
                appointments.reason,
                appointments.status,

                patient_users.name AS patient_name,

                doctor_users.name AS doctor_name,

                doctors.specialization

            FROM appointments

            JOIN patients
                ON appointments.patient_id = patients.id

            JOIN users AS patient_users
                ON patients.user_id = patient_users.id

            JOIN doctors
                ON appointments.doctor_id = doctors.id

            JOIN users AS doctor_users
                ON doctors.user_id = doctor_users.id

            WHERE patient_users.phone = %s

            ORDER BY
                appointments.appointment_date DESC,
                appointments.appointment_time DESC
            """,
            (phone,)
        )

        appointments = cursor.fetchall()

        cursor.close()
        connection.close()

        # Store the search phone temporarily
        session["appointment_search_phone"] = phone

        return redirect(url_for("appointments"))


    # =====================================================
    # GET
    # =====================================================

    phone = session.pop(
        "appointment_search_phone",
        ""
    )

    appointments = []
    error = None

    if phone:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                appointments.id,
                appointments.token_number,
                appointments.appointment_date,
                appointments.appointment_time,
                appointments.consultation_type,
                appointments.reason,
                appointments.status,

                patient_users.name AS patient_name,

                doctor_users.name AS doctor_name,

                doctors.specialization

            FROM appointments

            JOIN patients
                ON appointments.patient_id = patients.id

            JOIN users AS patient_users
                ON patients.user_id = patient_users.id

            JOIN doctors
                ON appointments.doctor_id = doctors.id

            JOIN users AS doctor_users
                ON doctors.user_id = doctor_users.id

            WHERE patient_users.phone = %s

            ORDER BY
                appointments.appointment_date DESC,
                appointments.appointment_time DESC
            """,
            (phone,)
        )

        appointments = cursor.fetchall()

        cursor.close()
        connection.close()

        if not appointments:
            error = (
                "No appointments found for this phone number."
            )

    return render_template(
        "appointments.html",
        appointments=appointments,
        error=error,
        phone=phone
    )
@app.route("/admin/dashboard")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "admin_dashboard.html",
        user_name=session["user_name"]
    )

@app.after_request
def add_no_cache_headers(response):

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, "
        "post-check=0, pre-check=0, max-age=0"
    )

    response.headers["Pragma"] = "no-cache"

    response.headers["Expires"] = "0"

    return response
# ========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=False
    )

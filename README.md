# Padma Hospital Appointment Booking System



Padma Hospital Appointment Booking System is a web application for managing hospital appointments.



Patients can view doctors, book appointments, receive an appointment token, and check their appointment details. Doctors can log in to their dashboard, view their appointments, and update appointment status.



The application was built using Flask and MySQL and is deployed using Railway.



## Features

### Patient

- View hospital information

- View doctors and their specializations

- Book an appointment

- Receive an appointment token

- Search for an appointment using a phone number

- View appointment details

- Check appointment status



### Doctor

- Doctor login

- Doctor dashboard

- View assigned appointments

- View patient information

- Manage appointment status

- Secure logout


## Appointment Process


1. The patient selects a doctor.

2. The patient chooses an available date and time.

3. The patient enters the required information.

4. The appointment is saved in the database.

5. A token number is assigned to the appointment.

6. The patient can search for the appointment using their phone number.

7. The doctor can view the appointment from the dashboard.

8. The doctor can update the appointment status after the consultation.



## Technologies Used

- Python

- Flask

- MySQL

- HTML

- CSS

- Jinja2

- Git

- GitHub

- Railway



## Database

The application uses MySQL to store hospital, doctor, patient, and appointment information.

The main tables are:

- `users`

- `doctors`

- `patients`

- `appointments`

- `doctor\_availability`

- `hospitals`



## Authentication



Doctors have separate login access to the doctor dashboard.



The application uses sessions to control access to protected doctor pages.



## Running Locally



### 1. Clone the repository



```bash

git clone <your-github-repository-url>

cd padma-hospital-booking



### 2. Install dependencies



```bash

pip install -r requirements.txt



### 3. Set up MySQL



Create the required database and import the SQL schema from:



database/schema.sql



### 4. Configure the database



Set the required database connection values using environment variables.



Do not commit database passwords or other private credentials to GitHub.



### 5. Start the application



```bash

python app.py



## The application will normally be available at:



 http://127.0.0.1:5000



## Deployment

	The application is deployed using Railway.



The Flask application uses environment variables to connect to the production MySQL database.



## What I Learned While building this project, I worked with:


Flask routes and templates

MySQL database connections

SQL queries

Authentication and sessions

Form handling

Appointment management

Token generation

Git and GitHub

Environment variables

Deploying a Flask application

Connecting a deployed application to a cloud database



## Future Improvements

Email or SMS appointment notifications

Appointment cancellation

Admin dashboard

Appointment filtering

Password reset

Appointment reports



## Author
	Sai Charan

Padma Hospital Appointment Booking System


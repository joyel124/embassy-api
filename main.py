from flask import Flask, jsonify, request
from flaskext.mysql import MySQL
from flask_restful import Resource, Api
from flask_jwt_extended import JWTManager  ## pip install flask-jwt-extended
from flask_jwt_extended import create_access_token
from flask_cors import CORS  ## pip install flask-cors
import bcrypt  ## pip install bcrypt
import resend

app = Flask(__name__)
CORS(app)
mysql = MySQL()
api = Api(app)

app.config['JWT_SECRET_KEY'] = 'embassy'  # semilla para generar token
jwt = JWTManager(app)

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'rypc202302'
app.config['MYSQL_DATABASE_DB'] = 'EEUU_EMBASSY'
app.config['MYSQL_DATABASE_HOST'] = '20.42.82.191'
app.config['MYSQL_DATABASE_PORT'] = 3306

resend.api_key = "re_K2iwFf2B_BTCjbgLLRjsCW7ynuoBs5SvS"  # API key de resend

mysql.init_app(app)


class Users(Resource):
    def get(self):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()
            getUsers = """select First_Name,
                          Last_Name,
                          Email,
                          Password,
                          Looking_Appointment
                          from User"""
            cursor.execute(getUsers)
            rows = cursor.fetchall()
            return jsonify(rows)
        except Exception as e:
            print(e)
        finally:
            cursor.close()
            conn.close()


class Appointments(Resource):
    def get(self):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()
            getAppointments = """select *
                          from Appointment"""
            cursor.execute(getAppointments)
            rows = cursor.fetchall()
            return jsonify(rows)
        except Exception as e:
            print(e)
        finally:
            cursor.close()
            conn.close()


class User(Resource):
    def get(self, ID):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.execute("select * from User where ID = %s", ID)
            rows = cursor.fetchall()
            return jsonify(rows)
        except Exception as e:
            print(e)
        finally:
            cursor.close()
            conn.close()


class Login(Resource):
    def post(self):  # Cambiado a POST
        try:
            conn = mysql.connect()
            cursor = conn.cursor()

            Email = request.form['Email']
            Password = request.form['Password']

            print(Email)
            print(Password)

            # Consulta solo con el Email
            cursor.execute("SELECT * FROM User WHERE Email = %s", Email)
            user = cursor.fetchone()

            print(user)

            # Verifica si el usuario existe y compara el hash de la contraseña
            if user and bcrypt.checkpw(Password.encode('utf-8'), user[4].encode('utf-8')):
                access_token = create_access_token(identity=Email)
                return jsonify(access_token=access_token)
            else:
                return jsonify({"msg": "Email o contraseña incorrectos"}), 401
        except Exception as e:
            print(e)
            return jsonify({"msg": "Error al procesar la solicitud"}), 500
        finally:
            cursor.close()
            conn.close()


class Register(Resource):
    def post(self):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()

            First_Name = request.form['First_Name']
            Last_Name = request.form['Last_Name']
            Email = request.form['Email']
            Password = request.form['Password']

            password_hash = bcrypt.hashpw(Password.encode('utf-8'), bcrypt.gensalt())

            insertUser = """INSERT INTO User(First_Name, Last_Name, Email,
                            Password)
                            VALUES
                            (%s,%s,%s,%s);"""
            cursor.execute(insertUser, (First_Name, Last_Name, Email,
                                        password_hash))
            conn.commit()
            response = jsonify(message='User added successfully.', id=cursor.lastrowid)
            response.status_code = 200
        except Exception as e:
            print(e)
            response = jsonify('Failed to add user.')
            response.status_code = 400
        finally:
            cursor.close()
            conn.close()
            return response


class Appointment(Resource):
    def get(self, Appointment_ID):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.execute("select * from Appointment where Appointment_ID = %s", Appointment_ID)
            rows = cursor.fetchall()
            return jsonify(rows)
        except Exception as e:
            print(e)
        finally:
            cursor.close()
            conn.close()


class NewAppointment(Resource):
    def post(self):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()
            _Appointment_Date = request.form['Appointment_Date']
            _Employee_ID = request.form['Employee_ID']

            get_emails_query = """SELECT Email FROM User WHERE Looking_Appointment = 1"""
            cursor.execute(get_emails_query)
            rows = cursor.fetchall()
            email_list = [row[0] for row in rows]

            print(email_list)

            insertAppointment = """INSERT INTO Appointment(Appointment_Date, Is_Available, Employee_ID)
                                   VALUES (%s, %s, %s);"""
            cursor.execute(insertAppointment, (_Appointment_Date, True, _Employee_ID))
            conn.commit()

            params = {
                "from": "Embassy <noreply@joyel.tech>",
                "to": email_list,
                "subject": "New Appointment available!",
                "html": "<strong>New Appointment available!</strong>",
            }
            email = resend.Emails.send(params)
            print(email)

            response = jsonify(message='Appointment added successfully.', id=cursor.lastrowid)
            response.status_code = 200
        except Exception as e:
            print(e)
            response = jsonify('Failed to add appointment.')
            response.status_code = 400
        finally:
            cursor.close()
            conn.close()
            return response


class AppointmentsByDate(Resource):
    def get(self):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()

            appointment_date = request.args.get('date')

            query = """SELECT * FROM Appointment WHERE DATE(Appointment_Date) = %s"""
            cursor.execute(query, (appointment_date,))

            appointments = cursor.fetchall()

            result = [{"appointment_id": row[0], "appointment_date": row[1], "is_available": row[2], "user_id": row[4]}
                      for row in appointments]

            return jsonify(result)

        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()


class AppointmentsByEmail(Resource):
    def get(self):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()

            Email = request.args.get('email')

            print(Email)

            cursor.execute('SELECT ID FROM User WHERE Email = %s', Email)
            ID = cursor.fetchone()
            print(ID)

            cursor.execute('SELECT * FROM Appointment WHERE User_ID = %s', ID)

            appointments = cursor.fetchall()

            result = [{"appointment_id": row[0], "appointment_date": row[1], "is_available": row[2], "user_id": row[4]}
                      for row in appointments]

            response = jsonify(result)
            response.status_code = 200
        except Exception as e:
            print(e)
            response = jsonify(message='No appointments found')
            response.status_code = 400
        finally:
            cursor.close()
            conn.close()
            return response


class UserByEmail(Resource):
    def get(self):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()
            Email = request.args.get('Email')
            cursor.execute('SELECT ID, First_Name, Last_Name, Email, Looking_Appointment FROM User WHERE Email = %s',
                           Email)
            rows = cursor.fetchone()
            response = jsonify(rows)
            response.status_code = 200
        except Exception as e:
            print(e)
            response = jsonify(message='Failed to get user')
            response.status_code = 400
        finally:
            cursor.close()
            conn.close()
            return response


class UpdateStatus(Resource):
    def put(self):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()
            Email = request.form['Email']
            Looking_Appointment = request.form['Looking_Appointment']
            cursor.execute('UPDATE User SET Looking_Appointment = %s WHERE Email = %s', (Looking_Appointment, Email))
            conn.commit();
            response = jsonify(message='Status modified successfully')
            response.status_code = 200
        except Exception as e:
            print(e)
            response = jsonify(message='Failed to update status')
            response.status_code = 400
        finally:
            cursor.close()
            conn.close()
            return response


class AddUserIdAppointment(Resource):
    def patch(self):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()
            appointment_id = request.form['appointment_id']
            email = request.form['email']

            print(appointment_id)
            print(email)

            # Obtener el ID del usuario
            cursor.execute('SELECT ID FROM User WHERE Email = %s', email)
            user_id = cursor.fetchone()[0]

            print(user_id)

            # Actualizar el estado de la cita y asignar el User_ID
            cursor.execute('UPDATE Appointment SET Is_Available = %s, User_ID = %s WHERE Appointment_ID = %s',
                           (False, user_id, appointment_id))
            conn.commit()

            response = jsonify(message='Appointment status updated successfully')
            response.status_code = 200
        except Exception as e:
            print(e)
            response = jsonify(message='Failed to update appointment status')
            response.status_code = 400
        finally:
            cursor.close()
            conn.close()
            return response


class DeleteUserIdAppointment(Resource):
    def patch(self):
        try:
            conn = mysql.connect()
            cursor = conn.cursor()
            appointment_id = request.form['appointment_id']

            # Actualizar el estado de la cita y poner el User_ID en null
            cursor.execute('UPDATE Appointment SET Is_Available = %s, User_ID = %s WHERE Appointment_ID = %s',
                           (True, None, appointment_id))
            conn.commit()

            get_emails_query = """SELECT Email FROM User WHERE Looking_Appointment = 1"""
            cursor.execute(get_emails_query)
            rows = cursor.fetchall()
            email_list = [row[0] for row in rows]

            print(email_list)

            params = {
                "from": "Embassy <noreply@joyel.tech>",
                "to": email_list,
                "subject": "New Appointment available!",
                "html": "<strong>New Appointment available!</strong>",
            }
            email = resend.Emails.send(params)
            print(email)

            response = jsonify(message='Appointment status updated successfully')
            response.status_code = 200
        except Exception as e:
            print(e)
            response = jsonify(message='Failed to update appointment status')
            response.status_code = 400
        finally:
            cursor.close()
            conn.close()
            return response


api.add_resource(DeleteUserIdAppointment, '/delete-appointment-status', endpoint='delete-appointment-status')
api.add_resource(AddUserIdAppointment, '/add-appointment-status', endpoint='add-appointment-status')
api.add_resource(AppointmentsByDate, '/appointments-by-date', endpoint='appointments-by-date')
api.add_resource(Users, '/users', endpoint='users')
api.add_resource(User, '/user/<int:ID>', endpoint='user')
api.add_resource(Register, '/register', endpoint='register')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Appointments, '/appointments', endpoint='appointments')
api.add_resource(Appointment, '/appointment/<int:Appointment_ID>', endpoint='appointment')
api.add_resource(NewAppointment, '/newappointment', endpoint='newappointment')
api.add_resource(AppointmentsByEmail, '/appointments-by-email', endpoint='appointments-by-email')
api.add_resource(UserByEmail, '/userbyemail', endpoint='userbyemail')
api.add_resource(UpdateStatus, '/updatestatus', endpoint='updatestatus')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=False)

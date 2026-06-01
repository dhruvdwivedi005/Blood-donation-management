from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.http import HttpResponse

def show_users(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM users;")
        rows = cursor.fetchall()
    return render(request, 'users.html', {'data': rows})






def add_request(request):
    if request.method == 'POST':
        user_id = request.session.get('user_id')
        hospital_id = 1  # temporary

        blood_group = request.POST.get('blood_group')
        units = request.POST.get('units')

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO blood_request (user_id, hospital_id, blood_group, units_required)
                VALUES (%s, %s, %s, %s)
                """,
                [user_id, hospital_id, blood_group, units]
            )

        return redirect('/my-requests/')

    return render(request, 'add_request.html')





def login_view(request):
    if request.method == 'POST':
        contact = request.POST.get('contact')
        password = request.POST.get('password')
        role = request.POST.get('role')

        try:
            with connection.cursor() as cursor:

                if role == 'user':
                    cursor.execute(
                        "SELECT user_id FROM users WHERE contact=%s AND password=%s",
                        [contact, password]
                    )
                    user = cursor.fetchone()

                    if user:
                        request.session['user_id'] = user[0]
                        request.session['role'] = 'user'
                        return redirect('/user-dashboard/')

                elif role == 'hospital':
                    cursor.execute(
                        "SELECT hospital_id FROM hospital WHERE contact=%s AND password=%s",
                        [contact, password]
                    )
                    hospital = cursor.fetchone()

                    if hospital:
                        request.session['hospital_id'] = hospital[0]
                        request.session['role'] = 'hospital'
                        return redirect('/hospital-dashboard/')

            return render(request, 'login.html', {'error': 'Invalid contact or password'})

        except Exception as e:
            return render(request, 'login.html', {'error': str(e)})

    return render(request, 'login.html')


def signup_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        blood_group = request.POST.get('blood_group')
        contact = request.POST.get('contact')
        address = request.POST.get('address')
        password = request.POST.get('password')

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (name, blood_group, contact, address, password)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [name, blood_group, contact, address, password]
            )

        return redirect('/login/')

    return render(request, 'signup.html')

def user_dashboard(request):
    user_id = request.session.get('user_id')

    with connection.cursor() as cursor:

        # User Requests
        cursor.execute(
            "SELECT * FROM blood_request WHERE user_id=%s",
            [user_id]
        )
        requests = cursor.fetchall()

        # User Donations
        cursor.execute(
            "SELECT * FROM blood_donation WHERE user_id=%s",
            [user_id]
        )
        donations = cursor.fetchall()

    return render(request, 'user_dashboard.html', {
        'requests': requests,
        'donations': donations
    })


def hospital_dashboard(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM blood_request")
        requests = cursor.fetchall()

        cursor.execute("SELECT * FROM blood_donation")
        donations = cursor.fetchall()

    return render(request, 'hospital_dashboard.html', {
        'requests': requests,
        'donations': donations
    })


def my_requests(request):
    user_id = request.session.get('user_id')

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM blood_request WHERE user_id=%s",
            [user_id]
        )
        data = cursor.fetchall()

    return render(request, 'my_requests.html', {'data': data})

def my_donations(request):
    user_id = request.session.get('user_id')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT donation_id, donation_date, units, status
            FROM blood_donation
            WHERE user_id=%s
        """, [user_id])
        data = cursor.fetchall()

    return render(request, 'my_donations.html', {'data': data})


def logout_view(request):
    request.session.flush()
    return redirect('/login/')

def add_donation(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    if request.method == 'POST':
        donation_date = request.POST.get('donation_date')
        units = request.POST.get('units')
        hospital_id = 1

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO blood_donation 
                (user_id, hospital_id, donation_date, units, status)
                VALUES (%s, %s, %s, %s, 'PENDING')
                """,
                [user_id, hospital_id, donation_date, units]
            )

        return redirect('/my-donations/')

    return render(request, 'add_donation.html')


def hospital_requests(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT r.request_id, u.name, u.contact,
                   r.blood_group, r.units_required, r.status
            FROM blood_request r
            JOIN users u ON r.user_id = u.user_id
        """)
        data = cursor.fetchall()

    return render(request, 'hospital_requests.html', {'data': data})

def process_request_view(request, req_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("CALL process_request(%s);", [req_id])

        return redirect('/hospital-requests/')

    except Exception as e:
        error_msg = str(e)

        if "Not enough stock" in error_msg:
            error_msg = "Not enough stock available"
        elif "not found" in error_msg:
            error_msg = "Blood group not found"
        else:
            error_msg = "Something went wrong"

        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT r.request_id, u.name, u.contact,
                       r.blood_group, r.units_required, r.status
                FROM blood_request r
                JOIN users u ON r.user_id = u.user_id
            """)
            data = cursor.fetchall()

        return render(request, 'hospital_requests.html', {
            'data': data,
            'error': error_msg
        })

def approve_donation_view(request, d_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("CALL approve_donation(%s);", [d_id])

        return redirect('/hospital-donations/')

    except Exception as e:
        error_msg = str(e)

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT d.donation_id,
                    u.name,
                    u.contact,
                    u.blood_group,
                    d.units,
                    d.donation_date,
                    d.status
                FROM blood_donation d
                JOIN users u ON d.user_id = u.user_id
            """)
            data = cursor.fetchall()

        return render(request, 'hospital_donations.html', {
            'data': data,
            'error': error_msg
        })

def hospital_donations(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT d.donation_id,
                u.name,
                u.contact,
                u.blood_group,   
                d.units,         
                d.donation_date,
                d.status
            FROM blood_donation d
            JOIN users u ON d.user_id = u.user_id
        """)
        data = cursor.fetchall()

    return render(request, 'hospital_donations.html', {'data': data})


def blood_stock_view(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT blood_group, units_available FROM blood_stock")
        data = cursor.fetchall()

    return render(request, 'blood_stock.html', {'data': data})
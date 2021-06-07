import datetime
import math
import re
import time
from functools import wraps

from flask import Blueprint, request, render_template, url_for, redirect, session, flash

from models import Pool
from models import User, LoanRequest, Loan
from models import db

main = Blueprint('main', __name__)


# Decorator: checks if the user is logged in before allowing them access to a page which requires login
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for(".login"))

    return wrap


# Decorator: checks if the user is a bank manager before allowing them access to a page which requires bank
#            manager status
def bank_manager_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user_id" in session:
            user = User.query.filter_by(id=session["user_id"]).first()
            if user.is_bank_manager:
                return f(*args, **kwargs)
            else:
                return redirect(url_for(".index"))
        else:
            return redirect(url_for(".index"))

    return wrap


# A CHEAT TO MAKE ME A BANK ADMIN
@main.route("/adminify")
def adminify():
    user = User.query.filter_by(id=session["user_id"]).first()
    user.is_bank_manager = True
    db.session.commit()
    if "logged_in" in session:
        return redirect(url_for(".dashboard"))
    else:
        return render_template("index.html")

# If the user navigates to either "/" or "/index" and they are not logged in, they will be presented "index.html"
# If the user is already logged in, they will be redirected to the dashboard
@main.route("/")
@main.route("/index")
def index():
    if "logged_in" in session:
        return redirect(url_for(".dashboard"))
    else:
        return render_template("index.html")


# If the user navigates to "/login" they will be presented "login.html"
# If the user is already logged in, they will be redirected to the dashboard
@main.route("/login")
def login():
    if "logged_in" in session:
        return redirect(url_for(".dashboard"))
    else:
        return render_template("login.html")


# Removes session variables from the user:
# - "logged_in" which would allow the user to access pages which require the user to be logged in
# - "user_id" which allowed the user's information to be accessed from the database from anywhere on the site
@main.route("/logout")
@login_required
def logout():
    session.pop("logged_in", None)
    session.pop("user_id", None)
    return redirect(url_for(".index"))


# If the user navigates to "/sign_up" they will be presented "signup.html"
# If the user is already logged in, they will be redirected to the dashboard
@main.route("/sign_up")
def sign_up():
    if "logged_in" in session:
        return redirect(url_for(".dashboard"))
    else:
        return render_template("signup.html")


# Retrieves a user's information to render their account's dashboard
@main.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    # Get current user from database
    user = User.query.filter_by(id=session["user_id"]).first()

    # For each loan taken out by the user, we will update the amount accrued and date last updated
    for loan in user.loans:
        # Determine the number of days since the loan was approved
        approval_date = loan.date_approved
        current_date = int(time.time())
        seconds_since_approved = current_date - approval_date
        days_since_approved = math.floor(seconds_since_approved / 86400)

        # Calculate the interest that has accrued since the loan was approved (based on principal amount)
        daily_interest_rate = (loan.interest_rate / 365) / 100
        daily_interest = loan.principal_amount * daily_interest_rate  # 6.85ish
        interest_since_approval = daily_interest * days_since_approved  # 59,403.20

        # Subtract the amount that has already been accrued according to the database to get the interest since the
        # user's last visit
        interest = interest_since_approval - loan.amount_accrued

        # Update the loan in the database so that it can also be reflected on the page
        loan.amount_accrued += interest
        loan.amount_due = (loan.principal_amount + loan.amount_accrued) - loan.amount_paid
        db.session.commit()

    return render_template("dashboard.html", user=user)


# If the user navigates to "/pool_browser" they will be presented "pool_browser.html"
# If
@main.route("/pool_browser", methods=["GET", "POST"])
@login_required
def pool_browser():
    # Get the current user model using the user_id session variable
    user = User.query.filter_by(id=session["user_id"]).first()

    # Query the database to get a list of all pool categories so they can be placed in the drop down list
    unfiltered_categories = [item[0] for item in Pool.query.with_entities(Pool.category)]

    # Remove all duplicates from the list
    categories = []
    for c in unfiltered_categories:
        if c not in categories:
            categories.append(c)

    # Query the database for a list of all loan pools
    pools = Pool.query.all()

    # If a post request occurs, the user likely hit the "Go" button next to the category list
    if request.method == "POST":
        # Get the chosen category from the drop down list
        chosen_category = request.form.get("category_list")

        # If the user selected "All" just launch the page without filtering the loan pools
        if chosen_category == "All":
            return render_template("pool_browser.html", categories=categories, pools=pools, user=user)

        # Create a new array containing only pools that match the chosen category
        # Once the array is created, set the pools array equal to it
        temp = []
        for pool in pools:
            if pool.category == chosen_category:
                temp.append(pool)
        pools = temp

    # Launch pool_browser.html with the appropriate variables
    return render_template("pool_browser.html", categories=categories, pools=pools, user=user)


@main.route("/pool_contribution", methods=["GET", "POST"])
@login_required
def pool_contribution():
    # Get the user from the session variable
    user = User.query.filter_by(id=session["user_id"]).first()

    # If an error occurs while processing the pool_contribution form, the pool_id will be placed
    # in a session variable because if it isn't, the pool_id from the form earlier is lost
    #
    # First, check if the ID is in the session variable, if it is not, the user must have come
    # straight from the pool_browser page
    if "temp_pool_id" in session:
        pool_id = session["temp_pool_id"]
        session.pop("temp_pool_id", None)
    else:
        pool_id = request.form.get("pool_id")

    # Get the pool model from the database using the pool_id
    pool = Pool.query.filter_by(id=pool_id).first()

    # Display "pool_contribution.html" with the required variables passed
    return render_template("pool_contribution.html", user=user, pool=pool)


@main.route("/loan_request", methods=["GET", "POST"])
@login_required
def loan_request():
    # Get the user from the session variable
    user = User.query.filter_by(id=session["user_id"]).first()

    # If an error occurs while processing the createLoanRequest form, the poolId will be placed in a session variable
    # because if it isn't, the poolId from the form earlier is lost
    # First, check if the ID is in the session variable, if it is not, the user must have come from the poolBrowser page
    if "temp_pool_id" in session:
        pool_id = session["temp_pool_id"]
        session.pop("temp_pool_id", None)
    else:
        pool_id = request.form.get("pool_id")

    # Get the pool model from the database using the pool_id
    pool = Pool.query.filter_by(id=pool_id).first()

    # Display "loan_request.html" with the required variables passed
    return render_template("request_loan.html", user=user, pool=pool)


# Routes the user to the account management page which accepts multiple parameters required for the info found on it
@main.route("/account", methods=["GET", "POST"])
@login_required
def account():
    # Get current user from database
    user = User.query.filter_by(id=session["user_id"]).first()

    # Display "account.html"
    return render_template("account.html", user=user)


'''
=======================================
|           BANK MANAGEMENT           |
=======================================
'''


#
@main.route("/bank_management", methods=["GET", "POST"])
@login_required
@bank_manager_required
def bank_management():
    # Get current user from database
    user = User.query.filter_by(id=session["user_id"]).first()

    # Get all loan requests for the loan requests table
    loan_requests = LoanRequest.query.all()

    # Display "bank_management.html" with all of the required arguments
    return render_template("bank_management.html", user=user, loan_requests=loan_requests)


@main.route("/approveLoanRequest", methods=["POST"])
@login_required
@bank_manager_required
def approveLoanRequest():
    # Grab the interest rate from the text box. If no interest rate is specified, set it to 2%.
    interest_rate = request.form.get("interest rate")

    if interest_rate == "":
        interest_rate = "2"

    # Makes sure whatever was entered by the user is actually a number. If it isn't, an error message will be displayed.
    if not re.match(r'^[1-9]\d*(\.\d{1,2})?$', interest_rate):
        flash("Please enter a valid number", "approveLoanRequestError")
        return redirect(url_for(".bankManagement"))

    # Now that we know it is a number, we can covert it to a float
    interestRate = float(interest_rate)

    # Make sure the number entered is between 0-100. If it isn't, an error message will be displayed
    if interestRate > 100:
        flash("Please enter a number between 0-100", "approveLoanRequestError")
        return redirect(url_for(".bankManagement"))

    # Get the loan id from the hidden field in the form and create a loanRequest object with it
    loanRequestId = request.form.get("loanRequestId")
    loanRequest = LoanRequest.query.filter_by(id=loanRequestId).first()

    # Create loan model and add it to the database
    loan = Loan(loanRequest.amount, interestRate, int(time.time()), loanRequest.user_id)
    db.session.add(loan)

    # Delete the loan request from the database
    LoanRequest.query.filter_by(id=loanRequestId).delete()

    # Query the pool taken from and subtract the amount taken from it
    pool = Pool.query.filter_by(id=loanRequest.pool_id).first()
    pool.amount -= loanRequest.amount

    # Save the changes to the database
    db.session.commit()

    return redirect(url_for(".bankManagement"))


@main.route("/approve_loan", methods=["GET", "POST"])
@login_required
@bank_manager_required
def approve_loan():
    # Get the loan request ID from the hidden tag and get a loan model/object
    loan_request_id = request.form.get("loan_request_id")
    loan_request = LoanRequest.query.filter_by(id=loan_request_id).first()

    return render_template("approve_loan.html", loan_request=loan_request)

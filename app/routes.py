import datetime
import time

from flask import Blueprint, request, render_template, url_for, redirect, session, flash
from functools import wraps

from database import db
from models import User, PoolContribution, LoanRequest, Loan
from models import Pool
from models import BankAccount
import bcrypt
import re

main = Blueprint('main', __name__)

'''
==================================
|           DECORATORS           |
==================================
'''


# Creates a decorator which indicates that the page accessed requires a login
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for(".login"))

    return wrap


# Creates a decorator which indicates that the page accessed requires the user to be a bank manager
def bank_manager_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user_id" in session:
            user = User.query.filter_by(id=session["user_id"]).first()
            if user.isBankManager:
                return f(*args, **kwargs)
            else:
                return redirect(url_for(".index"))
        else:
            return redirect(url_for(".index"))

    return wrap


'''
==================================
|           HOME PAGE            |
==================================
'''


# Retrieves and renders index.html whenever the server is accessed without a specific page defined
@main.route("/")
def index():
    if "logged_in" in session:
        return redirect(url_for(".dashboard"))
    else:
        return render_template("index.html")


'''
===========================================
|           LOGIN/LOGOUT/SIGNUP           |
===========================================
'''


# Retrieves and renders login.html whenever user accesses /login if GET method is performed
# Checks to see if the user's credentials are valid if POST method is performed
@main.route("/login", methods=["GET", "POST"])
def login():
    # If the user is already logged in, redirect them to dashboard.html
    if "logged_in" in session:
        return redirect(url_for(".dashboard"))

    # If an error occurs, this will be set to a string with an error message
    error = None

    # If the user submits the form
    if request.method == "POST":
        # Get the user's sign in information from the text boxes
        username = request.form["username"]
        password = request.form["password"]

        # If either of the text boxes were left empty, give the user an error message
        if username == "" or password == "":
            error = "Please fill out the required fields"
            return render_template("login.html", error=error)

        # Find the user in the database based on the username they entered
        user = User.query.filter_by(username=username).first()

        # If the user is found in the database set a session variable indicating they are logged in
        # then redirect them to the proper page
        if user:
            # Check if the password in the database matches the password that was entered
            if bcrypt.checkpw(password.encode("utf-8"), user.password):
                # Grant the user the required session variables
                session["logged_in"] = True
                session["user_id"] = user.id
                session["active_bank_account_id"] = user.bank_accounts[0].id

                return redirect(url_for(".index"))
            else:
                error = "Username/password is incorrect. Please try again"
        else:
            error = "Username/password is incorrect. Please try again."

    return render_template("login.html", error=error)


# Removes session variables from the user:
# - "logged_in" which would allow the user to access pages which require the user to be logged in
# - "user_id" which allowed the user's information to be accessed from the database from anywhere
@main.route("/logout")
@login_required
def logout():
    session.pop("logged_in", None)
    session.pop("user_id", None)
    session.pop("active_bank_account_id", None)
    return redirect(url_for(".index"))


# Retrieves and renders signup.html when the user navigates to /signup
# - Processes information from the form if filled out correctly. This information is used to create a user account
#   in the database. Once that is done, the user is given the "logged_in" and "user_id" session variables
# - If the form is not filled out correctly or the username is already taken, an error message is displayed for the user
@main.route("/signup", methods=["GET", "POST"])
def signup():
    # If the username entered by the user is already in use, this variable will change to an error
    # message which will be displayed on the template
    error = None

    # If the user submits the form
    if request.method == "POST":
        # Gather all data needed and put it into the User model
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        username = request.form["username"]
        password = request.form["password"]

        # Make sure each of the text boxes are filled with the required information
        # If not, give the user an error message
        if firstname == "" or lastname == "" or username == "" or password == "":
            error = "Please fill out each text box to continue."
            return render_template("signup.html", error=error)

        # Encrypt the password provided by the user before creating the database model
        password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # Make a User model with the information provided by the user
        user = User(firstname, lastname, username, password)

        # Checks if the username entered is already in the database
        found_user = User.query.filter_by(username=username).first()

        # If the username already exists, notify the user via dynamic HTML
        # Otherwise the user will be added to the database and redirected
        if found_user:
            error = "This username has already been taken! Please try again."
        else:
            # Add the user to the database
            db.session.add(user)
            db.session.commit()

            # Retrieve the user from the database so that the user's ID can be accessed and assigned to a session var
            user = User.query.filter_by(username=username).first()
            session["logged_in"] = True
            session["user_id"] = user.id

            # Create a default bank account for the user
            defaultAccount = BankAccount("Checking", 0, user.id)
            db.session.add(defaultAccount)
            db.session.commit()

            # Retrieve the bank account from the user model so it can be assigned to a session var
            session["active_bank_account_id"] = user.bank_accounts[0].id

            # Redirect to the dashboard
            return redirect(url_for(".dashboard"))

    # If the user simply accesses the page or refreshes, serve the signup.html page
    return render_template("signup.html", error=error)


'''
=================================
|           DASHBOARD           |
=================================
'''


# Retrieves a user's information to render their account's dashboard
@main.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    # Get current user from database
    user = User.query.filter_by(id=session["user_id"]).first()

    # Get the active bank account using the session variable
    bankAccount = BankAccount.query.filter_by(id=session["active_bank_account_id"]).first()

    # get loans and loan requests
    loan_requests = user.loan_requests
    loans = user.loans

    for loan in loans:
        # Format the date before starting the page
        loan.format_date_given = datetime.datetime.fromtimestamp(loan.date_given).strftime('%m/%d/%Y')

    return render_template("dashboard.html", user=user, loan_requests=loan_requests, loans=loans, bankAccount=bankAccount)


'''
====================================
|           POOL BROWSER           |
====================================
'''


# Retrieves information needed to properly render poolBrowser.html from the database and displays it
@main.route("/poolBrowser", methods=["GET", "POST"])
@login_required
def poolBrowser():
    # Get current user from database
    user = User.query.filter_by(id=session["user_id"]).first()

    # Set to "All" by default so that pools of all categories show up unless specifically requested by user
    chosenCategory = "All"

    # Query the pool table for a list of all categories found in the category field
    categoryQuery = [item[0] for item in Pool.query.with_entities(Pool.category)]
    # Remove duplicates from the list
    categories = []
    for c in categoryQuery:
        if c not in categories:
            categories.append(c)

    # Query the pool table for a list of all pools
    pools = Pool.query.all()

    # POST occurs when the user clicks the "go" button to switch categories
    if request.method == "POST":
        # Set the chosenCategory variable to whatever the user chose from the drop down list
        chosenCategory = request.form.get("categoryList")

        # If the user selected "All", simply launch the webpage without filtering pools
        if chosenCategory == "All":
            return render_template("poolBrowser.html", chosenCategory=chosenCategory, categories=categories,
                                   pools=pools, user=user)

        # Loop through the list of pools and only keep pools which match the chosen category
        temp = []
        for pool in pools:
            if pool.category == chosenCategory:
                temp.append(pool)
        pools = temp

    # Get active bank account to display towards the top
    bankAccount = BankAccount.query.filter_by(id=session["active_bank_account_id"])

    return render_template("poolBrowser.html", chosenCategory=chosenCategory, categories=categories,
                           pools=pools, user=user, bankAccount=bankAccount)


# Form function for the poolBrowser page
# - Transfers money from the user's bank account to the pool they chose to contribute to based on what they entered
#   in the "contribute" text box
@main.route("/contributeToPool", methods=["POST"])
@login_required
def contributeToPool():
    # Get the pool being used from the template
    poolId = request.form.get("poolId")
    pool = Pool.query.filter_by(id=poolId).first()

    # Get the user from session variable
    user = User.query.filter_by(id=session["user_id"]).first()

    # Get the active bank account using the session variable
    bankAccount = BankAccount.query.filter_by(id=session["active_bank_account_id"]).first()

    # Validate that the user actually entered a number
    amountContributed = request.form.get("contribute")
    if not re.match(r'^[1-9]\d*(\.\d{1,2})?$', amountContributed):
        flash("Please enter a valid number to make a request")
        return redirect(url_for(".poolBrowser"))

    # Get the amount from the textbox
    amountContributed = float(amountContributed)

    # If the amount contributed is greater than the amount the user has in their bank account, give error message
    if amountContributed > bankAccount.micro_dollars:
        flash("You do not have enough funds in your account to make this contribution")
        return redirect(url_for(".poolBrowser"))

    # Add the amount to the pool amount
    # Subtract the amount from the user's bank account
    # Create a new pool contribution
    pool.amount = pool.amount + amountContributed
    bankAccount.micro_dollars = bankAccount.micro_dollars - amountContributed
    poolContribution = PoolContribution(amountContributed, user.id, pool.id)
    db.session.add(poolContribution)
    db.session.commit()

    return redirect(url_for(".poolBrowser"))


# Form function for the poolBrowser page
# - Creates a new loan request in the database using the amount entered by the user in the "request" text box
@main.route("/requestFromPool", methods=["POST"])
@login_required
def requestFromPool():
    # Get the pool being used from the template
    poolId = request.form.get("poolId")
    pool = Pool.query.filter_by(id=poolId).first()

    # Get the user from session variable
    user = User.query.filter_by(id=session["user_id"]).first()

    # Get the active bank account using the session variable
    bankAccount = BankAccount.query.filter_by(id=session["active_bank_account_id"]).first()

    # validate that the user actually entered a number
    amountRequested = request.form.get("request")
    if not re.match(r'^[1-9]\d*(\.\d{1,2})?$', amountRequested):
        flash("Please enter a valid number to make a request")
        return redirect(url_for(".poolBrowser"))

    # Get the amount from the textbox
    amountRequested = float(amountRequested)

    # If the amount requested is greater than the amount in the pool, give error message
    if amountRequested > pool.amount:
        flash("You cannot request an amount that is greater than what the pool contains")
        return redirect(url_for(".poolBrowser"))

    # Create a loan request in the database
    usersName = user.firstname + " " + user.lastname
    loanRequest = LoanRequest(amountRequested, user.id, usersName, bankAccount.id, pool.id, pool.name, pool.amount)
    db.session.add(loanRequest)
    db.session.commit()

    return redirect(url_for(".poolBrowser"))


'''
==========================================
|           ACCOUNT MANAGEMENT           |
==========================================
'''


# Routes the user to the account management page which accepts multiple parameters required for the info found on it
@main.route("/accountManagement", methods=["GET", "POST"])
@login_required
def accountManagement():
    # Get current user from database
    user = User.query.filter_by(id=session["user_id"]).first()
    bankAccount = BankAccount.query.filter_by(id=session["active_bank_account_id"]).first()

    return render_template("accountManagement.html", user=user, bankAccount=bankAccount)


# Form function for the accountManagement page
# Switches the user's active bank account depending on what they choose from the bank account drop down list
@main.route("/switchBankAccounts", methods=["GET", "POST"])
@login_required
def switchBankAccounts():
    # Get the value from the account drop down list. The value contains the ID for each of the user's
    # bank accounts in the database
    session["active_bank_account_id"] = request.form.get("accountDropDown")
    return redirect(url_for(".accountManagement"))


# Form function for the accountManagement page
# Adds micro-dollars to the user's bank account based on what they enter into the "add funds" textbox
@main.route("/addFundsToActiveBankAccount", methods=["GET", "POST"])
@login_required
def addFundsToActiveBankAccount():
    # Get the user's current active bank account using the session variable
    bankAccount = BankAccount.query.filter_by(id=session["active_bank_account_id"]).first()

    # Get the amount the user put into the form and validate that it is actually a number
    amountToAdd = request.form.get("add funds")
    if not re.match(r'^[1-9]\d*(\.\d{1,2})?$', amountToAdd):
        flash("Please enter a valid number to make a request", "addFundsError")
        return redirect(url_for(".accountManagement"))

    # Add the amount to the user's bank account balance and update the database
    bankAccount.micro_dollars += float(amountToAdd)
    db.session.commit()

    return redirect(url_for(".accountManagement"))


# Form function for the accountManagement page
# - Creates a new bank account under the user's account
@main.route("/createNewBankAccount", methods=["POST"])
@login_required
def createNewBankAccount():
    # Get account name from the form
    accountName = request.form.get("account name")

    # Give the user an error message if the textbox is empty
    if accountName == "":
        flash("Please fill out all of the text boxes", "createBankAccountMissingFieldError")
        return redirect(url_for(".accountManagement"))

    # Create new bank account object and commit it to the database
    bankAccount = BankAccount(accountName, 0, session["user_id"])
    db.session.add(bankAccount)
    db.session.commit()

    return redirect(url_for(".accountManagement"))


# Form function for the accountManagement page
# - Changes the user's information. Whatever piece of information they choose from the drop down list is what will get
#   changed. User's will enter what they want to change their information to in the first text box of the form and they
#   will confirm that it is them by entering their password into the second.
@main.route("/changeUserInformation", methods=["GET", "POST"])
@login_required
def changeUserInformation():
    # Get user information from database
    user = User.query.filter_by(id=session["user_id"]).first()

    # Get information from the form
    infoToChange = request.form.get("infoDropDown")
    changeTo = request.form.get("newInformation")
    password = request.form.get("password")

    # Make sure all text boxes are actually properly filled out
    if changeTo == "" or password == "":
        flash("You must fill out the required text fields", "editInfoError")
        return redirect(url_for(".accountManagement"))

    # Check if password matches password found in database, then change the requested item
    if bcrypt.checkpw(password.encode("utf-8"), user.password):
        if infoToChange == "first name":
            user.firstname = changeTo
        elif infoToChange == "last name":
            user.lastname = changeTo
        elif infoToChange == "username":
            user.username = changeTo
        elif infoToChange == "password":
            user.password = changeTo
    else:
        flash("Password incorrect - please try again", "editInfoError")
        return redirect(url_for(".accountManagement"))

    # Save the change to the database
    db.session.commit()
    flash("Your information was changed successfully!", "editInfoSuccess")
    return redirect(url_for(".accountManagement"))


'''
=======================================
|           BANK MANAGEMENT           |
=======================================
'''


#
@main.route("/bankManagement", methods=["GET", "POST"])
@login_required
@bank_manager_required
def bankManagement():
    # Get current user from database
    user = User.query.filter_by(id=session["user_id"]).first()
    # Get all loan requests
    loanRequests = LoanRequest.query.all()

    return render_template("bankManagement.html", user=user, loanRequests=loanRequests)


@main.route("/createNewPool", methods=["POST"])
@login_required
@bank_manager_required
def createNewPool():
    # Get all required information from the form
    name = request.form.get("pool name")
    category = request.form.get("pool category")
    amount = request.form.get("starting amount")

    # validate that the text boxes were actually filled
    if name == "" or category == "" or amount == "":
        flash("You must fill all of the text boxes", "createNewPoolError")
        return redirect(url_for(".bankManagement"))

    # validate the amount to make sure it's actually a number
    if not re.match(r'^[1-9]\d*(\.\d{1,2})?$', amount):
        flash("Please enter a valid number", "createNewPoolError")
        return redirect(url_for(".bankManagement"))

    # Create the pool model and add it to the database
    pool = Pool(name, category, amount)
    db.session.add(pool)
    db.session.commit()

    return redirect(url_for(".bankManagement"))


@main.route("/approveLoanRequest", methods=["POST"])
@login_required
@bank_manager_required
def approveLoanRequest():
    # Grab the interest rate from the text box. If no interest rate is specified, set it to 2%.
    interestRate = request.form.get("interest rate")

    if interestRate == "":
        interestRate = "2"

    # Makes sure whatever was entered by the user is actually a number. If it isn't, an error message will be displayed.
    if not re.match(r'^[1-9]\d*(\.\d{1,2})?$', interestRate):
        flash("Please enter a valid number", "approveLoanRequestError")
        return redirect(url_for(".bankManagement"))

    # Now that we know it is a number, we can covert it to a float
    interestRate = float(interestRate)

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


@main.route("/denyLoanRequest", methods=["POST"])
@login_required
@bank_manager_required
def denyLoanRequest():
    # Get the loan id from the hidden field in the form and delete loanRequest object with it
    loanRequestId = request.form.get("loanRequestId")
    LoanRequest.query.filter_by(id=loanRequestId).delete()

    # Save the changes to the database
    db.session.commit()

    return redirect(url_for(".bankManagement"))
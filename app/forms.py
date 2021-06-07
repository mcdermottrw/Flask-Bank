import random

from flask import Blueprint, request, url_for, redirect, flash, session
import re
import bcrypt

from models import db, User, BankAccount, Pool, PoolContribution, LoanRequest

# Register the blueprint for this file
form = Blueprint('form', __name__)


# Login // Attempt to login to the site
@form.route("/attempt_login", methods=["POST"])
def attempt_login():
    # Get the user's sign-in information from the form's text boxes
    username = request.form["username_input"]
    password = request.form["password_input"]

    # Validate that neither of the text boxes were left empty
    # If either of them are, give the user an error message
    if text_is_blank(username) or text_is_blank(password):
        flash("You must fill all fields to continue", "attempt_login_error")
        return redirect(url_for("main.login"))

    # Find the user in the database based on the username they entered
    user = User.query.filter_by(username=username).first()

    # If the username is not found within the database, give the user an error message
    if not user:
        flash("Your username/password is incorrect - please try again", "attempt_login_error")
        return redirect(url_for("main.login"))

    # Check if the password from the database matches the password from the input box on the form
    # If it doesn't, display an error message
    if not bcrypt.checkpw(password.encode("utf-8"), user.password):
        flash("Your username/password is incorrect - please try again", "attempt_login_error")
        return redirect(url_for("main.login"))

    # Since the user passed all of the validation checks, give them the session variables required for site navigation
    session["user_id"] = user.id
    session["logged_in"] = True

    # Redirect the user to the dashboard now that they are logged in
    return redirect(url_for("main.dashboard"))


@form.route("/attempt_sign_up", methods=["POST"])
def attempt_sign_up():
    # Gather all of the inputs from the form and put them into the appropriate variables
    first_name = request.form["first_name_input"]
    last_name = request.form["last_name_input"]
    username = request.form["username_input"]
    password = request.form["password_input"]

    # Validate that none of the fields were left blank
    # If any were, display an error message
    if text_is_blank(first_name) or text_is_blank(last_name) or text_is_blank(username) or text_is_blank(password):
        flash("You must fill all fields to continue", "attempt_sign_up_error")
        return redirect(url_for("main.sign_up"))

        # Query the database to see if the chosen username is already taken (they must be unique)
    if User.query.filter_by(username=username).first():
        flash("The username you chose has already been taken - please try again", "attempt_sign_up_error")
        return redirect(url_for("main.sign_up"))

    # Encrypt the user's password input
    password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    # Create a user model to be possibly put into the database (pending validation)
    user = User(first_name, last_name, username, password)

    # Add the user to the database and save changes
    db.session.add(user)
    db.session.commit()

    # Query the user from the database so that their ID can be accessed and assigned to the session variable
    user = User.query.filter_by(username=username).first()
    session["user_id"] = user.id
    session["logged_in"] = True

    # Now that the user is in the database, we will create a default bank account for them (checking)
    # This loop generates a random account number for the bank account until it is found to be unique
    # to all others in the database
    while True:
        account_number = random.randint(5000000000, 5999999999)
        if not BankAccount.query.filter_by(account_number=account_number).first():
            break

    # Create the bank account with a balance of 0 and add it to the database
    bank_account = BankAccount(user.id, "Checking", 0)
    db.session.add(bank_account)
    db.session.commit()

    # Redirect to the dashboard
    return redirect(url_for("main.dashboard"))


# Pool Browser // Contribute to loan pool
# - Creates a new contribution entry within the database and adds the funds to the pool the user contributed to
@form.route("/contribute_to_pool", methods=["POST"])
def contribute_to_pool():
    # Fetch the user's model from the database
    user = User.query.filter_by(id=session["user_id"]).first()

    # Get the pool from the form
    pool_id = request.form.get("pool_id")
    pool = Pool.query.filter_by(id=pool_id).first()

    # Get the bank account the user would like to use from the form
    bank_account_id = request.form.get("bank_account_select")
    bank_account = BankAccount.query.filter_by(id=bank_account_id).first()

    # Get the amount the user would like to contribute from the text box
    amount_to_contribute = request.form.get("amount_to_contribute_input")

    # Make sure the amountToContribute field is not blank and that the user entered a valid number
    if text_is_blank(amount_to_contribute):
        flash("You must enter an amount to continue.", "pool_form_error")
        session["temp_pool_id"] = pool.id
        return redirect(url_for("main.pool_contribution"))

    if text_is_not_currency(amount_to_contribute):
        flash("Please enter a valid number to continue.", "pool_form_error")
        session["temp_pool_id"] = pool.id
        return redirect(url_for("main.pool_contribution"))

    # Now that checks are complete, convert amountToContribute from string to float
    amount_to_contribute = float(amount_to_contribute)

    # Make sure the user isn't trying to contribute more than they have in their bank account
    if amount_to_contribute > bank_account.balance:
        flash("You attempted to contribute more than you have in your bank account!", "pool_form_error")
        session["temp_pool_id"] = pool.id
        return redirect(url_for("main.pool_contribution"))

    # Add the amount contributed to the loan pool
    pool.amount += amount_to_contribute

    # Subtract the amount contributed from the user's bank account
    bank_account.balance -= amount_to_contribute

    # Create a new pool contribution entry
    pool_contribution = PoolContribution(user.id, pool.id, amount_to_contribute)

    # Save all changes to the database
    db.session.add(pool_contribution)
    db.session.commit()

    # Return the the pool browser page with a message of success
    f_amount_to_contribute = "${:,.2f}".format(amount_to_contribute)
    flash("You have contributed " + f_amount_to_contribute + " to " + pool.name + "!", "pool_form_success")
    return redirect(url_for("main.pool_browser"))


# Pool Browser // Create loan request
# - Creates a new loan request entry within the database to be approved by a bank admin later
@form.route("/create_loan_request", methods=["POST"])
def create_loan_request():
    # Fetch the user's model from the database
    user = User.query.filter_by(id=session["user_id"]).first()

    # Get the pool from the form
    pool_id = request.form.get("pool_id")
    pool = Pool.query.filter_by(id=pool_id).first()

    # Get the bank account the user would like to use from the form
    bank_account_id = request.form.get("bank_account_select")
    bank_account = BankAccount.query.filter_by(id=bank_account_id).first()

    # Get the amount the user requested from the text box
    amount_to_request = request.form.get("amount_to_request_input")

    # Make sure the amountToRequest field is not blank and that the user entered a valid number
    if text_is_blank(amount_to_request):
        flash("You must enter an amount to continue.", "pool_form_error")
        session["temp_pool_id"] = pool.id
        return redirect(url_for("main.loan_request"))

    if text_is_not_currency(amount_to_request):
        flash("Please enter a valid number to continue.", "pool_form_error")
        session["temp_pool_id"] = pool.id
        return redirect(url_for("main.loan_request"))

    # Now that checks are complete, convert amountToContribute from string to float
    amount_to_request = float(amount_to_request)

    # Make sure the user isn't trying to contribute more than they have in their bank account
    if amount_to_request > pool.amount:
        flash("You attempted to request more than the loan pool contains.", "pool_form_error")
        session["temp_pool_id"] = pool.id
        return redirect(url_for("main.loan_request"))

    # Create the loan request model
    loan_request = LoanRequest(user.id, bank_account_id, pool_id, amount_to_request)

    # Save the loan request in the database
    db.session.add(loan_request)
    db.session.commit()

    # Return the the pool browser page with a message of success
    f_amount_to_request = "${:,.2f}".format(amount_to_request)
    flash("You have requested " + f_amount_to_request + " from " + pool.name + "!", "pool_form_success")
    return redirect(url_for("main.pool_browser"))


# Account Management // Create new bank account
# - Creates a new bank account in the database that is linked to the user via a foreign key
# - Uses the name that the user inputs
@form.route("/create_new_bank_account", methods=["POST"])
def create_new_bank_account():
    # Fetch the user's model from the database
    user = User.query.filter_by(id=session["user_id"]).first()

    # Fetch the account name from the form
    account_name = request.form.get("bank_account_name_input")

    # Make sure the user actually filled in the text box
    if text_is_blank(account_name):
        flash("Please name your account to continue.", "create_new_bank_account_error")
        return redirect(url_for("main.account"))

    # Loop generates random account numbers and checks the database for matching ones until a unique one is found
    while True:
        account_number = random.randint(5000000000, 5999999999)
        account_exists = BankAccount.query.filter_by(account_number=account_number).first()
        if not account_exists:
            break

    # Create the new bank account starting with $0
    bank_account = BankAccount(user.id, account_name, 0)

    # Add and commit the new bank account to the database
    db.session.add(bank_account)
    db.session.commit()

    # Return to the account management page with a message of success
    success_message = "Bank account created! - " + bank_account.account_name + " [" + str(bank_account.account_number) + "]"
    flash(success_message, "create_new_bank_account_success")
    return redirect(url_for("main.account"))


# Account Management // Add funds to bank account
# - Retrieves the bank account ID from the form and uses it to retrieve the bank account from the database
# - Retrieves the amount to add from the form and validates that it's a valid value
# - Adds the money to the users bank account and updates the database to reflect
@form.route("/add_funds_to_bank_account", methods=["POST"])
def add_funds_to_bank_account():
    # Get the chosen bank account's id from the select element
    bank_account_id = request.form.get("bank_account_select")
    bank_account = BankAccount.query.filter_by(id=bank_account_id).first()

    # Get the amount the user wants to add from the input box
    funds_to_add = request.form.get("add_funds_input")

    # Validate that the user entered a valid value, send error message if not
    if text_is_blank(funds_to_add) or text_is_not_currency(funds_to_add):
        flash("Please enter a valid number to continue.", "add_funds_error")
        return redirect(url_for("main.account"))

    # Convert fundsToAdd string to float
    funds_to_add = float(funds_to_add)

    # Add the amount to the user's bank account balance and update the database
    bank_account.balance += funds_to_add
    db.session.commit()

    f_funds_to_add = "${:,.2f}".format(funds_to_add)
    f_account_balance = "${:,.2f}".format(bank_account.balance)
    success_message = "You have added " + f_funds_to_add + " to " + bank_account.account_name + " [" + \
                     str(bank_account.account_number) + "]. It's balance is now " + f_account_balance + "!"

    flash(success_message, "add_funds_success")
    return redirect(url_for("main.account"))


# Account Management // Update user information
# - Updates the database to reflect the data found in the input boxes of the form
# - If nothing is found in any of the inputs, an error message will be displayed
@form.route("/update_user_information", methods=["POST"])
def update_user_information():
    # Fetch the user's model from the database
    user = User.query.filter_by(id=session["user_id"]).first()

    # Get the information from the form
    first_name = request.form.get("first_name_input")
    last_name = request.form.get("last_name_input")
    username = request.form.get("username_input")

    # Make sure that none of the text boxes were left blank
    if text_is_blank(first_name) or text_is_blank(last_name) or text_is_blank(username):
        flash("Please fill all fields to continue.", "update_user_information_error")
        return redirect(url_for("main.account"))

    # Since none are blank, update the database to reflect the text in the form
    user.first_name = first_name
    user.last_name = last_name
    user.username = username
    db.session.commit()

    # Return to the account management page with a message of success
    flash("Information updated successfully!", "update_user_information_success")
    return redirect(url_for("main.account"))


# Account Management // Update user password
# - Gets the user's current password input and new password inputs from form
# - Makes sure all fields were filled, the current password matches the password in the database, and that
#   the new password input and confirm new password input actually match
# - Encrypts the new password and updates the database
@form.route("/update_user_password", methods=["POST"])
def update_user_password():
    # Fetch the user's model from the database
    user = User.query.filter_by(id=session["user_id"]).first()

    # Get all fields from the form
    current_password = request.form.get("current_password_input")
    new_password = request.form.get("new_password_input")
    confirm_new_password = request.form.get("confirm_new_password_input")

    # Make sure all fields are not blank
    if text_is_blank(current_password) or text_is_blank(new_password) or text_is_blank(confirm_new_password):
        flash("Please fill all fields to continue.", "update_user_password_error")
        return redirect(url_for("main.account"))

    # Check if the current password input matches the user's password in the database
    # If it doesn't, send the user an error message
    if not bcrypt.checkpw(current_password.encode("utf-8"), user.password):
        flash("The password you've entered under 'Current Password' is incorrect.", "update_user_password_error")
        return redirect(url_for("main.account"))

    # Make sure that new password and confirm new password match
    if not new_password == confirm_new_password:
        flash("'New Password' and 'Confirm New Password' did not match.", "update_user_password_error")
        return redirect(url_for("main.account"))

    # Set the user's new password on the database model and update the database to reflect the changes
    user.password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
    db.session.commit()

    # Let the user know that the operation was successful
    flash("Your password has been changed successfully!", "update_user_password_success")
    return redirect(url_for("main.account"))


# Bank Admin // Create new loan pool
# - Gather fields from the form
# - Validate them
# - Create new pool model and commit to database
@form.route("/create_new_loan_pool", methods=["POST"])
def create_new_loan_pool():
    # Get all fields from the form
    pool_name = request.form.get("pool_name_input")
    pool_category = request.form.get("pool_category_input")
    starting_amount = request.form.get("starting_amount_input")

    # Validate that all fields were filled
    if text_is_blank(pool_name) or text_is_blank(pool_category) or text_is_blank(starting_amount):
        flash("You must fill out all fields to continue.", "create_new_pool_error")
        return redirect(url_for("main.bank_management"))

    # Validate that starting amount is valid currency
    if text_is_not_currency(starting_amount):
        flash("Please enter a valid amount under 'starting amount'", "create_new_pool_error")
        return redirect(url_for("main.bank_management"))

    # Create pool model and commit to the database
    pool = Pool(pool_name, pool_category, float(starting_amount))
    db.session.add(pool)
    db.session.commit()

    # Return with a message of success
    success_message = "You have created " + pool.name + " [" + pool.category + "] with a starting amount of " + "${:,.2f}".format(pool.amount)
    flash(success_message, "create_new_pool_success")
    return redirect(url_for("main.bank_management"))


# Bank Management // Approve loan request
# -
@form.route("/approve_loan_request", methods=["POST"])
def approve_loan_request():
    return "."


# Bank Management // Deny loan request
# - Deletes the chosen loan request from the database
@form.route("/deny_loan_request", methods=["POST"])
def deny_loan_request():
    # Get the ID for the loan request from the hidden field within the form
    loan_request_id = request.form.get("loan_request_id")

    # Delete the loan request using SQLAlchemy and update the database to reflect the changes made
    LoanRequest.query.filter_by(id=loan_request_id).delete()
    db.session.commit()

    # Return to the bank management page
    return redirect(url_for("main.bank_management"))


# Validation function to check if the text passed is blank
def text_is_blank(text):
    if text is None or text == "":
        return True
    return False


# Validation function to check if the text passed is valid for currency
# - Text must be in the forms ###, ###.#, or ###.## and only be numbers in order to return true
def text_is_not_currency(text):
    if not re.match(r'^[1-9]\d*(\.\d{1,2})?$', text):
        return True
    return False

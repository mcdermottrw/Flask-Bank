import datetime

from sqlalchemy.orm import relationship
from database import db


'''
Models are a part of SQLAlchemy which allows us to create objects and convert those instances to entries/rows in our
SQLite database.
'''


# User Model - relates to "user" table in database
class User(db.Model):
    # Defines the database table's name
    __tablename__ = "user"

    # Defines and gives attributes to fields in the table
    id = db.Column(db.Integer, primary_key=True)  # SQLAlchemy requires primary keys
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)  # Usernames must be unique
    password = db.Column(db.String(100))
    isBankManager = db.Column(db.Integer)

    # Defines a one-to-many relationship with the models specified in relationship()
    # - The relationship() method returns an array of all rows that contain a foreign key from this model
    #   from the specified table
    bank_accounts = relationship("BankAccount")
    pool_contributions = relationship("PoolContribution")
    loans = relationship("Loan")
    loan_requests = relationship("LoanRequest")

    # Standard constructor for the model
    # - isBankManager is set to default -- the only way a user can be made a bank manager is by editing the
    #                                    database directly via a database editor
    # - Variables which refer to one to many relationships are set as empty lists by default
    def __init__(self, firstname, lastname, username, password, isBankManager=0, bank_accounts=[], pool_contributions=[], loans=[], loan_requests=[]):
        self.firstname = firstname
        self.lastname = lastname
        self.username = username
        self.password = password
        self.isBankManager = isBankManager
        self.bank_accounts = bank_accounts
        self.pool_contributions = pool_contributions
        self.loans = loans
        self.loan_requests = loan_requests


# BankAccount Model - relates to "bank_account" table in database
class BankAccount(db.Model):
    __tablename__ = "bank_account"

    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100))
    micro_dollars = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Foreign key relates to a row in the user table

    def __init__(self, account_name, micro_dollars, user_id):
        self.account_name = account_name
        self.micro_dollars = micro_dollars
        self.user_id = user_id


# Pool Model - relates to "pool" table in database
class Pool(db.Model):
    __tablename__ = "pool"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category = db.Column(db.String(100))
    amount = db.Column(db.Float)
    pool_contributions = relationship("PoolContribution")
    loan_requests = relationship("LoanRequest")

    def __init__(self, name, category, amount, pool_contributions=[], loan_requests=[]):
        self.name = name
        self.category = category
        self.amount = amount
        self.pool_contributions = pool_contributions
        self.loan_requests = loan_requests


# PoolContribution Model - relates to "pool_contribution" table in database
class PoolContribution(db.Model):
    __tablename__ = "pool_contribution"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    pool_id = db.Column(db.Integer, db.ForeignKey("pool.id"))

    def __init__(self, amount, user_id, pool_id):
        self.amount = amount
        self.user_id = user_id
        self.pool_id = pool_id


# Loan Model - relates to "loan" table in database
class Loan(db.Model):
    __tablename__ = "loan"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    interest_rate = db.Column(db.Float)
    date_given = db.Column(db.Integer)  # dates will be recorded using Unix Time (number of seconds since Jan 1, 1970)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __init__(self, amount, interest_rate, date_given, user_id):
        self.amount = amount
        self.interest_rate = interest_rate
        self.date_given = date_given
        self.formatted_date_given = ""
        self.user_id = user_id


# LoanRequest Model - relates to "loan_request in database
class LoanRequest(db.Model):
    __tablename__ = "loan_request"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    requester_name = db.Column(db.String(100))
    account_id = db.Column(db.Integer, db.ForeignKey("bank_account.id"))
    pool_id = db.Column(db.Integer, db.ForeignKey("pool.id"))
    pool_name = db.Column(db.String(100))
    pool_amount = db.Column(db.Float)

    def __init__(self, amount, user_id, requester_name, account_id, pool_id, pool_name, pool_amount):
        self.amount = amount
        self.user_id = user_id
        self.requester_name = requester_name
        self.account_id = account_id
        self.pool_id = pool_id
        self.pool_name = pool_name
        self.pool_amount = pool_amount

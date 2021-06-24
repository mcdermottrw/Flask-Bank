import random
import time

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship

'''
Models are a part of SQLAlchemy which allows us to create objects and convert those instances to entries/rows in our
SQLite database.
'''

# Initialize database
db = SQLAlchemy()


# Connects to the "user" table in the database
class User(db.Model):
    # Defines the table name in the database
    __tablename__ = "user"

    # Defines and gives attributes to columns in the table
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    username = Column(String(100), unique=True)  # All usernames must be unique
    password = Column(String(100))
    is_bank_manager = Column(Boolean, default=False)

    # Defines one-to-many relationships with other models/tables
    # The models being referenced in relationship() are those that contain a foreign key which relates back to this
    # model (typically user_id). This function is particularly useful because it will return an array of models which
    # contain the foreign key that relates to the specific row of the user table
    bank_accounts = relationship("BankAccount")
    pool_contributions = relationship("PoolContribution")
    loans = relationship("Loan")
    # Backref will allow the LoanRequest model instance to access a User model instance which the foreign key in the
    # LoanRequest model relates to
    loan_requests = relationship("LoanRequest", backref="user")

    # Constructor that collects all of the data from the sign-up form which is all that is needed to create an entry
    # within the table
    def __init__(self, first_name, last_name, username, password):
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.password = password


# Connects to the "bank_account" table in the database
class BankAccount(db.Model):
    __tablename__ = "bank_account"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    account_name = Column(String(100))
    account_number = Column(Integer, unique=True)
    balance = Column(Float)

    loan_requests = relationship("LoanRequest", backref="bank_account")

    def __init__(self, user_id, account_name, balance):
        self.account_name = account_name
        self.user_id = user_id
        self.account_number = self.generateAccountNumber()
        self.balance = balance

    # Generates a random account number in the range 5000000000 to 5999999999
    @staticmethod
    def generateAccountNumber():
        # This loop generates a random account number for the bank account until it is found to be unique
        # to all others in the database
        while True:
            account_number = random.randint(5000000000, 5999999999)
            if not BankAccount.query.filter_by(account_number=account_number).first():
                break

        return account_number


# Connects to the "pool" table in the database
class Pool(db.Model):
    __tablename__ = "pool"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    category = Column(String(100))
    amount = Column(Float)

    pool_contributions = relationship("PoolContribution", backref="pool")
    loan_requests = relationship("LoanRequest", backref="pool")

    def __init__(self, name, category, amount):
        self.name = name
        self.category = category
        self.amount = amount


# Connects to the "pool_contribution" table in the database
class PoolContribution(db.Model):
    __tablename__ = "pool_contribution"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    pool_id = Column(Integer, ForeignKey("pool.id"))
    amount = Column(Float)

    def __init__(self, user_id, pool_id, amount):
        self.user_id = user_id
        self.pool_id = pool_id
        self.amount = amount


# Connects to the "loan" table in the database
class Loan(db.Model):
    __tablename__ = "loan"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    #
    principal_amount = Column(Float)
    amount_accrued = Column(Float, default=0)
    amount_paid = Column(Float, default=0)
    amount_due = Column(Float)
    # All dates will be represented through Unix time
    date_approved = Column(Integer, default=int(time.time()))
    date_due = Column(Integer)
    #
    interest_rate = Column(Float)

    def __init__(self, user_id, principal_amount, amount_due, date_due, interest_rate):
        self.user_id = user_id
        self.principal_amount = principal_amount
        self.date_due = date_due
        self.interest_rate = interest_rate


# Connects to "loan_request" in the database
class LoanRequest(db.Model):
    __tablename__ = "loan_request"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    account_id = Column(Integer, ForeignKey("bank_account.id"))
    pool_id = Column(Integer, ForeignKey("pool.id"))
    amount = Column(Float)

    def __init__(self, user_id, account_id, pool_id, amount):
        self.user_id = user_id
        self.account_id = account_id
        self.pool_id = pool_id
        self.amount = amount

import os
import datetime
import pytz

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")



@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    if request.method == "GET":

        # Get stock symbol and share from database
        portfolio = db.execute("SELECT stockname, SUM(share) AS total_share FROM bought WHERE userid = ? GROUP BY stockname ORDER BY total_share", session["user_id"])
        stock_values = []
        total_trade = 0

        # Iterate over each company in portfolio
        for company in portfolio:
            stock_info = lookup(company['stockname'])


            # Assuming lookup returns a dictionary with stock information
            if stock_info:
                stock_info['total_share'] = company['total_share']
                stock_info['total'] = company['total_share'] * stock_info['price']
                stock_values.append(stock_info)
                #stock_values.append(company['total_share'])
            total_trade = total_trade + stock_info['total']

        cash = 10000 - total_trade
        cash = "{:.2f}".format(cash)
        total_investment = float(total_trade) + float(cash)
        #return apology("TODO")

        return render_template("index.html", stock_values = stock_values, cash = cash, total_investment = total_investment)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        # Check stock symbol
        if not request.form.get("symbol"):
            return apology("must provide stock symbol", 400)

        # Check stock price
        stock_value = {}
        stock_value = lookup(request.form.get("symbol"))

        if stock_value == None:
            return apology("None", 400)

        #try:
            #shares = int(request.form.get("shares"))
        #except ValueError:
            #return apology("shares must be a postive integer", 400)

        shares = request.form.get("shares")

        if not shares.isdigit():
            return apology("You cannot purchase partial shares")

        # Check if number of share is positive number
        if int(request.form.get("shares")) <= 0:
            return apology("must provide positive number", 400)

        #try:
            # Check stock price
            #stock_value = {}
            #stock_value = lookup(request.form.get("symbol"))

        #except TypeError:
            #return apology("None", 400)

        # Calculate amount to be spent
        amount_spent = stock_value["price"] * int(request.form.get("shares"))

        # Find cash that user have
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash = cash[0]['cash']
        #print(cash)

        if float(cash) < amount_spent:
            return apology("you dont have enough cash", 400)

        # Get the current date and time in the "US/Eastern" timezone
        current_time = datetime.datetime.now(pytz.timezone("US/Eastern"))

        db.execute("INSERT INTO bought(userid, stockname, stockprice, share, time) VALUES (?, ?, ?, ?, ?)", session["user_id"], stock_value["name"], stock_value["price"], int(request.form.get("shares")), current_time)

        # Redirect user to home page
        return redirect("/")

    else:
        # Render buy.html
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT stockname, share, stockprice, time from bought WHERE userid = ?", session["user_id"])
    print(history)
    return render_template("history.html", history = history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("symbol"):
            return apology("must provide stock symbol", 400)

        # Use lookup to get value
        stock_value = {}
        stock_value = lookup(request.form.get("symbol"))

        if stock_value == None:
            return apology("None", 400)


        return render_template("quoted.html", stock_value = stock_value)


    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
        # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure same password was submitted
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("must provide same password", 400)

        # Generate hashed password
        hashed_password = generate_password_hash(request.form.get("password"))

        # Insert into database
        name = request.form.get("username")
        db.execute("INSERT INTO users (username,hash) VALUES(?, ?)", name,hashed_password)

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")
    #return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
            # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("stock"):
            return apology("must select stock", 403)

        # Ensure password was submitted
        elif not request.form.get("num_share"):
            return apology("must provide number of share", 403)

        # Ensure password was submitted
        elif int(request.form.get("num_share")) < 0:
            return apology("must provide positive number of share", 403)

        # Check stock price
        stock_value = {}
        stock_value = lookup(request.form.get("stock"))

        # Get the current date and time in the "US/Eastern" timezone
        current_time = datetime.datetime.now(pytz.timezone("US/Eastern"))

        share_sold = int(request.form.get("num_share"))
        share_sold = -share_sold
        db.execute("INSERT INTO bought(userid, stockname, stockprice, share, time) VALUES (?, ?, ?, ?, ?)", session["user_id"], stock_value["name"], stock_value["price"], share_sold, current_time)


        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Get stock symbol and share from database
        portfolio = db.execute("SELECT stockname, SUM(share) AS total_share FROM bought WHERE userid = ? GROUP BY stockname ORDER BY total_share", session["user_id"])
        # Return company name
        company_list = []
        for company in portfolio:
            if company:
                company_list.append(company['stockname'])
                #print(company)
        #print(company_list)
        return render_template("sell.html", company_list = company_list)
    #return apology("TODO")

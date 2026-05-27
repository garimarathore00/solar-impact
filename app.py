from turtle import pd, rt
import pandas as pd
import plotly.express as px
import os

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secret123'

# DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODEL
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

# CREATE DB
with app.app_context():
    db.create_all()

# ---------------- ROUTES ---------------- #

# HOME
@app.route('/')
def index():
    return render_template('index.html')

# ABOUT
@app.route('/about')
def about():
    return render_template('about.html')

# REGISTER
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if not name or not email or not password:
                flash('All fields required', 'error')
                return redirect(url_for('register'))

            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(url_for('register'))

            if User.query.filter_by(email=email).first():
                flash('Email already exists', 'error')
                return redirect(url_for('register'))

            hashed_password = generate_password_hash(password)

            new_user = User(name=name, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            flash('🎉 Registration Successful! Login now.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            print(e)
            flash('Something went wrong', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

# LOGIN
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash('✅ Login Successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')

# DASHBOARD (Protected)
    

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    df = pd.read_csv("data.csv")
    df.columns = df.columns.str.strip().str.lower()

    total_events = len(df)
    avg_speed = round(df['speed'].mean(),2)
    max_speed = df['speed'].max()
    event_types = df['event_type'].nunique()
    geo_percent = round((df['potentially_geoeffective'].sum()/len(df))*100,2)

    return render_template(
        "dashboard.html",
        total_events=total_events,
        avg_speed=avg_speed,
        max_speed=max_speed,
        event_types=event_types,
        geo_percent=geo_percent
    )


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# RUN
if __name__ == '__main__':
    app.run(debug=True)
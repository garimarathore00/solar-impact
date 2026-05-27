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

    years = []
    if 'year' in df.columns:
        years = sorted(df['year'].dropna().unique().astype(int).tolist())
    elif 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist())
        
    cme_types = []
    if 'cme_type' in df.columns:
        cme_types = sorted(df['cme_type'].dropna().astype(str).unique().tolist())

    return render_template(
        "dashboard.html",
        total_events=total_events,
        avg_speed=avg_speed,
        max_speed=max_speed,
        event_types=event_types,
        geo_percent=geo_percent,
        years=years,
        cme_types=cme_types
    )

def speed_cat(x):
    if x < 500:
        return "Slow"
    elif x < 1000:
        return "Medium"
    else:
        return "Fast"

def style(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#000814",
        plot_bgcolor="#001d3d",
        font=dict(color="white", size=12),
        title=dict(
            x=0.5,
            font=dict(size=18, color="#00f7ff")
        ),
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified"
    )
    fig.update_traces(
        marker=dict(line=dict(width=0)),
        opacity=0.9
    )
    return fig

@app.route('/plot/<int:plot_id>')
def get_plot(plot_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    year = request.args.get('year')
    cme_type = request.args.get('cme_type')
    
    # Load and clean data
    df = pd.read_csv("data.csv")
    df.columns = df.columns.str.strip().str.lower()
    
    # Prep fields if not already populated correctly
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['hour'] = df['date'].dt.hour
    
    if 'speed' in df.columns:
        df['speed_category'] = df['speed'].fillna(0).apply(speed_cat)
    
    if 'direction' in df.columns:
        df['direction_bin'] = pd.cut(
            df['direction'],
            bins=[0, 90, 180, 270, 360],
            labels=['0-90', '90-180', '180-270', '270-360']
        )
        
    # Apply dynamic filters
    if year and year != 'All Years' and year != '':
        try:
            df = df[df['year'] == int(float(year))]
        except ValueError:
            pass
            
    if cme_type and cme_type != 'All CME Types' and cme_type != '':
        df = df[df['cme_type'].fillna("").astype(str).str.lower() == cme_type.lower()]
        
    fig = None
    
    try:
        if plot_id == 1:
            fig = px.line(df.groupby('year').size().reset_index(name='count'), x='year', y='count', title="Events Over Time")
        elif plot_id == 2:
            fig = px.pie(df, names='cme_type', title="CME Type", hole=0.4)
        elif plot_id == 3:
            fig = px.bar(df, x='speed_category', title="Speed Category")
        elif plot_id == 4:
            fig = px.histogram(df, x='speed', nbins=15, title="Speed Distribution")
        elif plot_id == 5:
            fig = px.box(df, y='speed', title="Speed Box")
        elif plot_id == 6:
            fig = px.bar(df, x='event_type', title="Event Type")
        elif plot_id == 7:
            fig = px.bar(df, x='source_location', title="Source Location")
        elif plot_id == 8:
            fig = px.bar(df, x='measurement_technique', title="Technique")
        elif plot_id == 9:
            fig = px.bar(df, x='catalog', title="Catalog")
        elif plot_id == 10:
            fig = px.scatter(df, x='speed', y='half_angle', title="Speed vs Angle")
        elif plot_id == 11:
            fig = px.bar(df.groupby('month').size().reset_index(name='count'), x='month', y='count', title="Month")
        elif plot_id == 12:
            fig = px.line(df.groupby('hour').size().reset_index(name='count'), x='hour', y='count', title="Hour")
        elif plot_id == 13:
            fig = px.area(df.groupby('year').size().reset_index(name='count'), x='year', y='count', title="Year Trend")
        elif plot_id == 14:
            fig = px.bar(df.groupby('quarter').size().reset_index(name='count'), x='quarter', y='count', title="Quarter")
        elif plot_id == 15:
            fig = px.histogram(df, x='hour', title="Hour Dist")
        elif plot_id == 16:
            fig = px.histogram(df, x='month', title="Month Dist")
        elif plot_id == 17:
            fig = px.box(df, x='month', y='speed', title="Speed vs Month")
        elif plot_id == 18:
            fig = px.box(df, x='hour', y='speed', title="Speed vs Hour")
        elif plot_id == 19:
            fig = px.line(df.groupby('day').size().reset_index(name='count'), x='day', y='count', title="Day")
        elif plot_id == 20:
            fig = px.line(df.groupby('day_of_year').size().reset_index(name='count'), x='day_of_year', y='count', title="Day of Year")
        elif plot_id == 21:
            fig = px.bar(df, x='speed_category', color='cme_type', title="Speed vs Type")
        elif plot_id == 22:
            fig = px.box(df, x='cme_type', y='speed', title="Speed vs Type Box")
        elif plot_id == 23:
            fig = px.histogram(df, x='speed', color='cme_type', title="Speed Type Dist")
        elif plot_id == 24:
            fig = px.scatter(df, x='speed', y='latitude', title="Speed vs Lat")
        elif plot_id == 25:
            fig = px.scatter(df, x='speed', y='longitude', title="Speed vs Lon")
        elif plot_id == 26:
            fig = px.box(df, x='speed_category', y='half_angle', title="Angle vs Speed Cat")
        elif plot_id == 27:
            fig = px.histogram(df, x='half_angle', title="Half Angle")
        elif plot_id == 28:
            fig = px.box(df, y='half_angle', title="Half Angle Box")
        elif plot_id == 29:
            fig = px.scatter(df, x='half_angle', y='latitude', title="Angle vs Lat")
        elif plot_id == 30:
            fig = px.scatter(df, x='half_angle', y='longitude', title="Angle vs Lon")
        elif plot_id == 31:
            fig = px.scatter(df, x='longitude', y='latitude', title="Lat vs Lon")
        elif plot_id == 32:
            fig = px.histogram(df, x='latitude', title="Lat Dist")
        elif plot_id == 33:
            fig = px.histogram(df, x='longitude', title="Lon Dist")
        elif plot_id == 34:
            fig = px.box(df, y='latitude', title="Lat Box")
        elif plot_id == 35:
            fig = px.box(df, y='longitude', title="Lon Box")
        elif plot_id == 36:
            fig = px.scatter(df, x='latitude', y='speed', title="Lat vs Speed")
        elif plot_id == 37:
            fig = px.scatter(df, x='longitude', y='speed', title="Lon vs Speed")
        elif plot_id == 38:
            fig = px.histogram(df, x='direction', title="Direction")
        elif plot_id == 39:
            fig = px.bar(df.groupby('direction_bin').size().reset_index(name='count'), x='direction_bin', y='count', title="Direction Bin")
        elif plot_id == 40:
            fig = px.scatter(df, x='direction', y='speed', title="Direction vs Speed")
        elif plot_id == 41:
            fig = px.pie(df, names='potentially_geoeffective', title="Geo Impact", hole=0.4)
        elif plot_id == 42:
            fig = px.box(df, x='potentially_geoeffective', y='speed', title="Speed vs Geo")
        elif plot_id == 43:
            fig = px.bar(df, x='cme_type', color='potentially_geoeffective', title="Type vs Geo")
        elif plot_id == 44:
            fig = px.bar(df, x='event_type', color='potentially_geoeffective', title="Event vs Geo")
        elif plot_id == 45:
            fig = px.histogram(df, x='speed', color='potentially_geoeffective', title="Speed Geo Dist")
        elif plot_id == 46:
            fig = px.box(df, y='half_angle', color='potentially_geoeffective', title="Angle vs Geo")
        elif plot_id == 47:
            fig = px.scatter(df, x='speed', y='latitude', color='potentially_geoeffective', title="Geo Scatter")
        elif plot_id == 48:
            fig = px.bar(df, x='measurement_technique', color='potentially_geoeffective', title="Tech vs Geo")
        elif plot_id == 49:
            fig = px.bar(df, x='catalog', color='potentially_geoeffective', title="Catalog vs Geo")
        elif plot_id == 50:
            fig = px.bar(df, x='source_location', color='potentially_geoeffective', title="Location vs Geo")
    except Exception as e:
        print(f"Error generating plot {plot_id}: {e}")
        
    if fig is None:
        fig = px.scatter(title=f"No Data Available for Plot {plot_id} under selected filters")
        
    fig = style(fig)
    return fig.to_html(include_plotlyjs='cdn', full_html=True)


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# RUN
if __name__ == '__main__':
    app.run(debug=True)
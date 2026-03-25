import json
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from app import app, db
from app.models import Locations, WeatherRecords
from datetime import datetime, timedelta
from app.forms import *
from app.ai import *
from flask_login import login_user, current_user, login_required, logout_user
from urllib.parse import urlsplit




@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = QueryForm()
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        location_input = request.form.get('location')
        is_valid = True

        if start_date and not end_date:
            is_valid = False
        if end_date and not start_date:
            is_valid = False
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            if start > end:
                is_valid = False
        if not location_input:
            is_valid = False

        if not is_valid:
            flash(
                "Invalid input. Location is required. Start date must be earlier than end date, or leave both date blank. Please try again.")
            return redirect((url_for('index')))


        # format of loc_data: {'lat':xxxx, 'lon': xxxx}
        loc_data = resolve_location(location_input)
        if not loc_data:
            flash("The input location doesn't exist.")
            return redirect((url_for('index')))

        # case1: No specific date
        if not start_date and not end_date:
            weather_info, error = get_weather(loc_data)
            if error:
                flash(error)
                return redirect(url_for('index'))

            weather_info, error = get_weather(loc_data)
            if error:
                flash(error)
                return redirect(url_for('index'))
            print("Weather_info: ",weather_info)

            loc = Locations.query.filter_by(formatted_address=weather_info['address']).first()
            if not loc:
                loc = Locations(input_query=location_input, formatted_address=weather_info['address'],
                                latitude=loc_data['lat'], longitude=loc_data['lon'])
                db.session.add(loc)
                db.session.flush()

            new_record = WeatherRecords(
                location_id = loc.id,
                temperature = weather_info['temp'],
                min_temp = weather_info['min_temp'],
                max_temp = weather_info['max_temp'],
                weather_description = weather_info['desc'],
                humidity = weather_info['humidity'],
                wind_speed = weather_info['wind_speed'],
                clouds = weather_info['clouds'],
                user_id = current_user.id
            )
            db.session.add(new_record)
            db.session.commit()
            session['last_query'] = {
                'type': 'current',
                'location': location_input,
                'address': weather_info['address'],
                'temperature': weather_info['temp'],
                'description': weather_info['desc'],
                'humidity': weather_info['humidity'],
                'wind_speed': weather_info['wind_speed'],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            flash(f"Successfully found and recorded the current weather of {weather_info['address']}")
            return redirect(url_for('index'))
        # case2: from a date to a date
        else:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            print(f"start {start}")
            print(f"end {end}")

            placeholder_address = f"{location_input} (Historical Data)"
            loc = Locations.query.filter_by(
                latitude=loc_data['lat'],
                longitude=loc_data['lon']
            ).first()
            if not loc:
                loc = Locations(
                    input_query=location_input,
                    formatted_address=placeholder_address,
                    latitude=loc_data['lat'],
                    longitude=loc_data['lon']
                )
                db.session.add(loc)
                db.session.flush()

            success_count = 0
            error_dates = []

            current_date = start
            while current_date <= end:
                print(current_date)

                existing = WeatherRecords.query.filter(
                    WeatherRecords.location_id == loc.id,
                    WeatherRecords.created_at >= datetime.combine(current_date, datetime.min.time()),
                    WeatherRecords.created_at < datetime.combine(current_date + timedelta(days=1), datetime.min.time())
                ).first()

                if existing:
                    logging.info(f"data {current_date} already exists.")
                    current_date += timedelta(days=1)
                    continue

                weather_info, error = get_historical_weather(loc_data['lat'], loc_data['lon'], current_date)

                if error:
                    logging.error(f"failed to get {current_date}: {error}")
                    error_dates.append(current_date.strftime('%Y-%m-%d'))
                    current_date += timedelta(days=1)
                    continue

                new_record = WeatherRecords(
                    location_id=loc.id,
                    temperature=weather_info['temp'],
                    min_temp=weather_info['min_temp'],
                    max_temp=weather_info['max_temp'],
                    weather_description=weather_info['desc'],
                    humidity=weather_info['humidity'],
                    wind_speed=weather_info['wind_speed'],
                    clouds=weather_info['clouds'],
                    date=datetime.combine(current_date, datetime.min.time()),
                    user_id=current_user.id
                )
                db.session.add(new_record)
                success_count += 1

                current_date += timedelta(days=1)


            db.session.commit()

            summary = {
                'type': 'historical',
                'location': location_input,
                'start_date': start.strftime('%Y-%m-%d'),
                'end_date': end.strftime('%Y-%m-%d'),
                'success_count': success_count,
                'error_dates': error_dates
            }
            session['last_query'] = summary

            if error_dates:
                flash(f"Successfully recorded {success_count} data but failed to load dates below:{', '.join(error_dates)}")
            else:
                flash(f"Successfully recorded {success_count} data（{start} to {end}）")

            return redirect(url_for('index'))

    records = WeatherRecords.query.order_by(WeatherRecords.created_at.desc()).all()
    last_query = session.pop('last_query', None)
    return render_template('index.html', form=form, records=records, last_query=last_query)


@app.route('/delete/<int:record_id>')
@login_required
def delete_record(record_id):
    record = WeatherRecords.query.get_or_404(record_id)
    db.session.delete(record)
    db.session.commit()
    flash("Record deleted.")
    return redirect(url_for('manage'))


@app.route('/export/json')
@login_required
def export_json():
    records = WeatherRecords.query.all()
    return jsonify([r.to_dict() for r in records])

@app.route('/manage', methods=['POST', 'GET'])
@login_required
def manage():
    records = WeatherRecords.query.filter_by(user_id=current_user.id).order_by(WeatherRecords.created_at.desc()).all()
    return render_template('manage.html', records=records)

@app.route('/update_record/<int:record_id>', methods=['POST', 'GET'])
@login_required
def update_record(record_id):
    record = WeatherRecords.query.get(record_id)
    form = UpdateForm()
    if form.validate_on_submit():
        is_valid=True
        if form.min_temp.data and form.max_temp.data and form.min_temp.data > form.max_temp.data:
            is_valid=False
            flash("Please input correct temperature range.")
        if form.min_temp.data and form.min_temp.data > record.temperature:
            is_valid=False
            flash("Please input correct temperature range.")
        if form.max_temp.data and form.max_temp.data > record.temperature:
            is_valid=False
            flash("Please input correct temperature range.")
        if form.clouds.data and (form.clouds.data < 0 or form.clouds.data > 100):
            is_valid=False
            flash("Please input correct Cloudiness range")

        if not is_valid:
            return redirect(url_for('update_record', record_id = record_id))


        record.min_temp = form.min_temp.data if form.min_temp.data else record.min_temp
        record.max_temp = form.max_temp.data if form.max_temp.data else record.max_temp
        record.wind_speed = form.wind_speed.data if form.wind_speed.data else record.wind_speed
        record.clouds = form.clouds.data if form.clouds.data else record.clouds
        record.weather_description = form.status.data if form.status.data else record.weather_description
        db.session.commit()
        flash('Successfully Updated', 'success')
        return redirect(url_for('manage'))
    else:
        flash("Update Failed.")

    return render_template('update_record.html', record_id=record_id, record=record, form=form)

@app.route('/search', methods=['POST', 'GET'])
@login_required
def search():
    records = WeatherRecords.query.order_by(WeatherRecords.date.desc()).all()
    return render_template('search.html', records=records)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)
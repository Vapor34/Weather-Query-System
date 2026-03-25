from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, PasswordField, BooleanField
from wtforms.fields.choices import SelectField
from wtforms.fields.datetime import DateField
from wtforms.fields.numeric import IntegerField, FloatField
from wtforms.validators import DataRequired, Length, Optional
from wtforms.validators import ValidationError,EqualTo
from datetime import date

from app.models import User
from app import db
import sqlalchemy as sa


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(
            User.username == username.data))
        if user is not None:
            raise ValidationError('Please use a different username.')


class QueryForm(FlaskForm):
    location = StringField("Location", validators=[DataRequired()])
    start_date = DateField("Start Date", validators=[Optional()])
    end_date = DateField("End Date", validators=[Optional()])
    submit = SubmitField("Search Info")


class UpdateForm(FlaskForm):
    min_temp = FloatField("Min Temp(°C)", validators=[Optional()])
    max_temp = FloatField("Max Temp(°C)", validators=[Optional()])
    wind_speed = FloatField("Wind Speed(m/s)", validators=[Optional()])
    clouds = IntegerField("Cloudiness(%)", validators=[Optional()])
    status = StringField("Status", validators=[Optional()])
    submit = SubmitField("Update")

from typing import Optional, List
from datetime import datetime
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(63), index=True,
                                                unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(255))

    records: Mapped[List["WeatherRecords"]] = relationship(back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Locations(db.Model):
    __tablename__ = 'locations'

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    input_query: Mapped[str] = mapped_column(sa.String(128), index=True)
    formatted_address: Mapped[str] = mapped_column(sa.String(256))
    latitude: Mapped[float] = mapped_column(sa.Float)
    longitude: Mapped[float] = mapped_column(sa.Float)

    records: Mapped[List["WeatherRecords"]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<Location {self.formatted_address}>'


class WeatherRecords(db.Model):
    __tablename__ = 'weatherrecords'

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(
        sa.ForeignKey('locations.id', ondelete='CASCADE'), nullable=False
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    temperature: Mapped[Optional[float]] = mapped_column(sa.Float)
    min_temp: Mapped[Optional[float]] = mapped_column(sa.Float)
    max_temp: Mapped[Optional[float]] = mapped_column(sa.Float)
    weather_description: Mapped[Optional[str]] = mapped_column(sa.String(128))
    humidity: Mapped[Optional[int]] = mapped_column(sa.Integer)
    wind_speed: Mapped[Optional[float]] = mapped_column(sa.Float)
    clouds: Mapped[Optional[int]] = mapped_column(sa.Integer)
    icon: Mapped[Optional[str]] = mapped_column(sa.String)

    external_data: Mapped[Optional[str]] = mapped_column(sa.Text)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow
    )
    date: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow
    )

    location: Mapped["Locations"] = relationship(back_populates="records")
    user: Mapped["User"] = relationship(back_populates="records")

    def to_dict(self):

        return {
            "id": self.id,
            "address": self.location.formatted_address,
            "temp": self.temperature,
            "humid": self.humidity,
            "desc": self.weather_description,
            "external_info": self.external_data,
            "query_time": self.created_at,
        }

    def __repr__(self):
        return f'<WeatherRecord {self.id} for {self.location_id}>'

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))
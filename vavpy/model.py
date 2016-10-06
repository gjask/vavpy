from peewee import Model, CharField, IntegerField, ForeignKeyField,\
    DateTimeField, BooleanField
import datetime
import random
import string
from playhouse import db_url


# __all__ = []
__all__ = ['Categories', 'Entry', 'Contact', 'Contestant', 'Start', 'Check']

_letters = string.ascii_letters + string.digits
db = db_url.connect('sqlite://test.db')


class BaseModel(Model):
    class Meta:
        database = db

    # def __new__(cls, *args, **kwargs):
    #     super(BaseModel, cls).__new__(cls, *args, **kwargs)
    #     __all__.append(cls.__name__)


class Categories(BaseModel):
    name = CharField()


class Contact(BaseModel):
    club = CharField(null=True)
    address = CharField(null=True)
    city = CharField(null=True)
    psc = CharField(null=True)
    country = CharField(null=True)
    phone = CharField()
    email = CharField()


class Entry(BaseModel):
    # code = CharField()
    created = DateTimeField(default=datetime.datetime.now)
    pass_code = CharField()
    contact = ForeignKeyField(Contact)

    @property
    def code(self):
        return '{}{}'.format(self.created.year, self.id)  # todo

    @staticmethod
    def new_passcode():
        return ''.join(ch for ch in random.choice(_letters))


class Contestant(BaseModel):
    name = CharField()
    category = ForeignKeyField(Categories)
    entry = ForeignKeyField(Entry, 'contestants')


class Start(BaseModel):
    contestant = ForeignKeyField(Contestant)
    number = IntegerField(index=True, unique=True)  # sequence=
    # time = DateTimeField()
    real_time = DateTimeField(null=True)
    disqualified = BooleanField(default=False)


# class Time(BaseModel):
#     gate = IntegerField()
#     line = IntegerField()
#     # number = ForeignKeyField()
#     number = IntegerField()
#     time = DateTimeField()


class Check(BaseModel):
    gate = IntegerField()
    line = IntegerField()
    # number = ForeignKeyField()
    number = IntegerField()
    points = IntegerField(default=0)
    time = DateTimeField(null=True)

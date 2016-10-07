from peewee import Model, CharField, IntegerField, ForeignKeyField,\
    DateTimeField, BooleanField, TimeField, PrimaryKeyField
import datetime
import random
import string
from playhouse import db_url


first_start = datetime.time(9, 30)  # todo move to database or setting
step = datetime.timedelta(seconds=30)


# __all__ = []
__all__ = ['Category', 'Entry', 'Contact', 'Contestant', 'Start', 'Check']

_letters = string.ascii_letters + string.digits
db = db_url.connect('sqlite:///test.db')


def dt_add(time, delta):
    realtime = datetime.datetime.combine(datetime.date.today(), time)
    realtime += delta
    return realtime.time()


def new_passcode():
    return ''.join(ch for ch in random.choice(_letters))


class BaseModel(Model):
    class Meta:
        database = db

    # def __new__(cls, *args, **kwargs):
    #     super(BaseModel, cls).__new__(cls, *args, **kwargs)
    #     __all__.append(cls.__name__)


class Category(BaseModel):
    name = CharField()

    def __unicode__(self):
        return self.name


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
    pass_code = CharField(default=new_passcode)
    contact = ForeignKeyField(Contact)

    @property
    def code(self):
        return '{}{}'.format(self.created.year, self.id)  # todo


class Contestant(BaseModel):
    name = CharField()
    category = ForeignKeyField(Category)
    entry = ForeignKeyField(Entry, 'contestants')


class Start(BaseModel):
    number = PrimaryKeyField()
    contestant = ForeignKeyField(Contestant, 'starts', unique=True)
    # number = IntegerField(index=True, unique=True)  # sequence=
    real_time = TimeField(null=True)
    disqualified = BooleanField(default=False)

    @property
    def time(self):
        return dt_add(first_start, step * (self.number - 1))

    # @classmethod
    # def schedule_entry(cls, entry):
    #     source = (Contestant
    #               .select(Contestant.id)
    #               .where(Contestant.entry == entry)
    #               )
    #     cls.insert_from([cls.contestant], source).execute()

    @classmethod
    def schedule_contestants(cls, contestants):
        cls.insert_many({'contestant': c} for c in contestants).execute()



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

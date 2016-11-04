from peewee import CharField, IntegerField, ForeignKeyField, DateTimeField,\
    BooleanField, PrimaryKeyField, Proxy
import datetime
import random
import string
import csv
from playhouse import db_url, flask_utils


# todo db.create_tables([], safe=True)

__all__ = ['Category', 'Entry', 'Contact', 'Contestant', 'Start', 'Check', 'db',
           'connect_manually']

_letters = string.ascii_letters + string.digits
db = flask_utils.FlaskDB()


def connect_manually(url, **kwargs):
    conn = db_url.connect(url, **kwargs)
    if isinstance(db.database, Proxy):
        db.database.initialize(conn)
    else:
        db.database = conn
    return db.database


def time2str(time_int):
    h, m, s = time_int // 3600, time_int % 3600 // 60, time_int % 60
    return '{:0>2}:{:0>2}:{:0>2}'.format(h, m, s)


def str2time(time_str):
    h, m, s = (int(n) for n in time_str.split(':'))
    return h * 3600 + m * 60 + s


def new_passcode():
    return ''.join(random.choice(_letters) for i in range(6))


first_start = str2time('09:30:00')  # todo move to database or setting
step = 30  # seconds


class Category(db.Model):
    name = CharField()

    def __unicode__(self):
        return self.name


class Contact(db.Model):
    club = CharField(null=True)
    address = CharField(null=True)
    city = CharField(null=True)
    psc = CharField(null=True)
    country = CharField(null=True)
    phone = CharField()
    email = CharField()


class Entry(db.Model):
    # code = CharField()
    created = DateTimeField(default=datetime.datetime.now)
    pass_code = CharField(default=new_passcode)
    contact = ForeignKeyField(Contact)

    @property
    def code(self):
        return '{}-{:0>4}'.format(self.created.strftime('%y'), self.id)

    @staticmethod
    def get_id(code):
        return int(code[-4:])


class Contestant(db.Model):
    name = CharField()
    category = ForeignKeyField(Category)
    entry = ForeignKeyField(Entry, 'contestants')


class Start(db.Model):
    number = PrimaryKeyField()
    contestant = ForeignKeyField(Contestant, 'starts', unique=True)
    # number = IntegerField(index=True, unique=True)  # sequence=
    # real_time = TimeField(null=True)
    real_time = IntegerField(null=True)
    disqualified = BooleanField(default=False)

    @property
    def time(self):
        # return dt_add(first_start, step * (self.number - 1))
        return first_start + step * (self.number - 1)

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


class Check(db.Model):
    gate = IntegerField()
    line = IntegerField()
    number = ForeignKeyField(Start, 'checks')
    points = IntegerField(default=0)
    time = IntegerField(null=True)

    @classmethod
    def from_csv(cls, file, gate):
        _step = 100
        query_list = list(cls._query_from_csv(file, gate))
        for i in range(-(-len(query_list) // _step)):
            cls.insert_many(query_list[i * _step:(i + 1) * _step]).execute()

    @staticmethod
    def _query_from_csv(file, gate):
        # todo rewrite using dictcsvreader
        reader = csv.reader(file)
        for count, line in enumerate(reader):
            try:
                if len(line) >= 3:
                    time = str2time(line[2])
                else:
                    time = None
                yield {
                    'gate': gate,
                    'line': count,
                    'number': int(line[0]),
                    'points': int(line[1]),
                    'time': time
                }
            except (ValueError, IndexError):
                continue


# todo create model and sql view
# class Results(db.Model):
#     pass

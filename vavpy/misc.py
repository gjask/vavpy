from .model import Start
import datetime


def update_time(number, h, m, s=0):
    # h, m, s = real_time_str.split(':')
    time = datetime.time(h, m, s)
    cnt = Start.get(number=number)
    cnt.real_time = time
    cnt.save()

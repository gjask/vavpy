from flask import Flask, render_template, abort, request, redirect, url_for

from vavpy.forms import *
from .model import *

app = Flask(__name__)


@app.route('/')
def dashboard_view():
    start_list = Start.select().order_by(Start.number)
    return render_template('dashboard.html', start_list=start_list)


@app.route('/entry/', methods=('GET', 'POST'))
@app.route('/entry/<int:entry_id>/', methods=('GET', 'POST'))
def entry_view(entry_id=None):
    if entry_id is not None:
        try:
            entry = Entry.get(id=entry_id)
        except Entry.DoesNotExist:
            abort(404)
        form = NewEntryForm(request.form, entry)
    else:
        form = NewEntryForm(request.form)

    if request.method == 'POST' and form.validate():
        return redirect(url_for('dashboard_view'))
    else:
        return render_template('entry.html', form=form)

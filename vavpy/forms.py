# from flask_wtf import Form
from wtforms import Form
from wtforms import FormField, FieldList, StringField
from wtfpeewee.orm import model_form

from vavpy.model import Contact, Contestant

# class SelfAwareForm(Form):
#     def is_submitted(self):
#         # todo


# class ContestantForm(Form):
#     name = StringField()
#     category = SelectField()  # todo choices dynamically


ContestantForm = model_form(Contestant, exclude=[Contestant.entry])
ContactForm = model_form(Contact)


class NewEntryForm(Form):
    contact = FormField(ContactForm)
    contestants = FieldList(FormField(ContestantForm), min_entries=1)


class FromCodeEntryForm(Form):
    code = StringField()

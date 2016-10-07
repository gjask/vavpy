# from flask_wtf import Form
from wtforms import Form
from wtforms import FormField, FieldList, StringField, SubmitField, \
    IntegerField, SelectField, HiddenField, validators
from wtforms.widgets import HiddenInput
from wtfpeewee.orm import model_form, ModelConverter, PrimaryKeyField

from vavpy.model import Contact, Contestant, Category

# class SelfAwareForm(Form):
#     def is_submitted(self):
#         # todo


# class ContestantForm(Form):
#     id = IntegerField()  # widget=HiddenInput())
#     name = StringField(validators=[validators.required])
#     category = SelectField(validators=[validators.required], choices=[])
#
#     # def __init__(self, *args, **kwargs):
#     #     cats = Category.select()
#     #     self.category.choices = [(cat.name, cat.name) for cat in cats]
#     #     super(ContestantForm, self).__init__(*args, **kwargs)


def handle_pk(model, field, **kwargs):
    return field.name, HiddenField()


inline_converter = ModelConverter({PrimaryKeyField: handle_pk})


ContestantForm = model_form(
    Contestant,
    exclude=['entry'],
    allow_pk=True,
    converter=inline_converter
)
ContactForm = model_form(Contact)


class NewEntryForm(Form):
    contact = FormField(ContactForm)
    contestants = FieldList(FormField(ContestantForm), min_entries=1)
    save = SubmitField('Save')
    paste = SubmitField('Save and Add')


class FromCodeEntryForm(Form):
    pass_code = StringField()
    paste = SubmitField('Add')

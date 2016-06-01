from unittest import mock

from django import forms
from django.test import TestCase, override_settings

from ..helpers import get_form_field, rabbit


class GetFormFieldTestCase(TestCase):

    SPEC = {
        "label": "Test",
        "read_only": False,
        "required": True,
    }

    def test_string_field(self):
        spec = self.SPEC.copy()
        spec.update({"type": "string", "max_length": 128})
        field = self._test_field(
            spec, forms.CharField, forms.widgets.TextInput)
        self.assertEqual(field.max_length, 128)

    def test_textarea_field(self):
        spec = self.SPEC.copy()
        spec.update({"type": "string"})
        field = self._test_field(
            spec, forms.CharField, forms.widgets.Textarea)
        self.assertIsNone(field.max_length)

    def test_email_field(self):
        spec = self.SPEC.copy()
        spec.update({"type": "email", "max_length": 128})
        field = self._test_field(
            spec, forms.EmailField, forms.widgets.EmailInput)
        self.assertEqual(field.max_length, 128)

    def test_choice_field(self):
        spec = self.SPEC.copy()
        spec.update({
            "type": "choice",
            "choices": [
                {"value": 1, "display_name": "Thing 1"},
                {"value": 2, "display_name": "Thing 2"}
            ]
        })
        field = self._test_field(
            spec, forms.ChoiceField, forms.widgets.Select)
        self.assertEqual(field.choices, [(1, "Thing 1"), (2, "Thing 2")])

    def test_integer_field(self):
        spec = self.SPEC.copy()
        spec.update({"type": "integer"})
        self._test_field(
            spec, forms.IntegerField, forms.widgets.NumberInput)

    def test_boolean_field(self):
        spec = self.SPEC.copy()
        spec.update({"type": "boolean"})
        self._test_field(
            spec, forms.BooleanField, forms.widgets.CheckboxInput)

    def test_date_field(self):
        spec = self.SPEC.copy()
        spec.update({"type": "date"})
        self._test_field(
            spec, forms.DateField, forms.widgets.DateInput)

    def test_datetime_field(self):
        spec = self.SPEC.copy()
        spec.update({"type": "datetime"})
        self._test_field(
            spec, forms.DateTimeField, forms.widgets.DateTimeInput)

    def test_optional_field(self):
        spec = self.SPEC.copy()
        spec.update({"type": "integer", "required": False})
        field = get_form_field(spec)
        self.assertIsInstance(field, forms.IntegerField)
        self.assertIsInstance(field.widget, forms.widgets.NumberInput)
        self.assertFalse(field.required)
        self.assertFalse(field.widget.is_required)

    def test_optional_choice_field(self):
        spec = {
            "type": "choice",
            "required": False,
            "choices": [
                {"value": 1, "display_name": "Thing 1"},
                {"value": 2, "display_name": "Thing 2"}
            ]
        }
        field = get_form_field(spec)
        self.assertIsInstance(field, forms.ChoiceField)
        self.assertIsInstance(field.widget, forms.widgets.Select)
        self.assertFalse(field.required)
        self.assertFalse(field.widget.is_required)
        self.assertEqual(
            field.choices, [("", ""), (1, "Thing 1"), (2, "Thing 2")])
        
    def _test_field(self, spec, form_field, widget):
        field = get_form_field(spec)
        self.assertIsInstance(field, form_field)
        self.assertIsInstance(field.widget, widget)
        self.assertTrue(field.required)
        self.assertTrue(field.widget.is_required)
        return field


class RabbitTestCase(TestCase):

    class FakeResponse(object):
        def __init__(self, status):
            self.status_code = status

    @override_settings(UI_SECRET="secret")
    def test_get(self):
        with mock.patch("alice.helpers.Rabbit.send_request") as send:
            send.return_value = self.FakeResponse(200)
            self.assertEqual(rabbit.get("https://notareal.url").status_code, 200)

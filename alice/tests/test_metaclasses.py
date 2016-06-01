from unittest import mock

from django import forms
from django.test import TestCase

from ..metaclasses import ReflectiveFormMetaclass


class FakeResponse(object):

    def __init__(self, data):
        self._json = data

    def json(self):
        return self._json


class ReflectiveFormMetaclassTestCase(TestCase):

    def test_text_field_creation(self):
        schema = {"max_length": 256, "type": "string"}
        field = self._test_field_creation(schema)
        self.assertEqual(field.max_length, 256)
        self.assertIsInstance(field, forms.CharField)
        self.assertIsInstance(field.widget, forms.widgets.TextInput)

    def test_textarea_field_creation(self):
        schema = {"type": "string"}
        field = self._test_field_creation(schema)
        self.assertIsNone(field.max_length)
        self.assertIsInstance(field, forms.CharField)
        self.assertIsInstance(field.widget, forms.widgets.Textarea)

    def test_email_field_creation(self):
        schema = {"max_length": 256, "type": "email"}
        field = self._test_field_creation(schema)
        self.assertEqual(field.max_length, 256)
        self.assertIsInstance(field, forms.EmailField)
        self.assertIsInstance(field.widget, forms.widgets.TextInput)

    def test_choice_field_creation(self):
        schema = {
            "type": "choice",
            "choices": [
                {"value": 1, "display_name": "Thing 1"},
                {"value": 2, "display_name": "Thing 2"}
            ]
        }
        field = self._test_field_creation(schema)
        self.assertIsInstance(field, forms.ChoiceField)
        self.assertIsInstance(field.widget, forms.widgets.Select)
        self.assertEqual(field.choices, [(1, "Thing 1"), (2, "Thing 2")])

    def test_integer_field_creation(self):
        schema = {"type": "integer"}
        field = self._test_field_creation(schema)
        self.assertIsInstance(field, forms.IntegerField)
        self.assertIsInstance(field.widget, forms.widgets.NumberInput)

    def test_boolean_field_creation(self):
        schema = {"type": "boolean"}
        field = self._test_field_creation(schema)
        self.assertIsInstance(field, forms.BooleanField)
        self.assertIsInstance(field.widget, forms.widgets.CheckboxInput)

    def test_date_field_creation(self):
        schema = {"type": "date"}
        field = self._test_field_creation(schema)
        self.assertIsInstance(field, forms.DateField)
        self.assertIsInstance(field.widget, forms.widgets.DateInput)

    def test_datetime_field_creation(self):
        schema = {"type": "datetime"}
        field = self._test_field_creation(schema)
        self.assertIsInstance(field, forms.DateTimeField)
        self.assertIsInstance(field.widget, forms.widgets.DateTimeInput)

    def test_optional_field_creation(self):
        schema = {"type": "integer", "required": False}
        field = self._test_field_creation(schema)
        self.assertIsInstance(field, forms.IntegerField)
        self.assertIsInstance(field.widget, forms.widgets.NumberInput)

    def test_optional_choice_field_creation(self):
        schema = {
            "type": "choice",
            "required": False,
            "choices": [
                {"value": 1, "display_name": "Thing 1"},
                {"value": 2, "display_name": "Thing 2"}
            ]
        }
        field = self._test_field_creation(schema)
        self.assertIsInstance(field, forms.ChoiceField)
        self.assertIsInstance(field.widget, forms.widgets.Select)
        self.assertEqual(
            field.choices, [("", ""), (1, "Thing 1"), (2, "Thing 2")])

    def test_skiped_field(self):

        with mock.patch("alice.metaclasses.rabbit.get") as mock_get:

            mock_get.return_value = FakeResponse({
                "test": {
                    "label": "Test",
                    "read_only": False,
                    "required": True,
                    "type": "integer"
                },
                "skipped": {
                    "label": "Skipped",
                    "read_only": False,
                    "required": True,
                    "type": "integer"
                }
            })

            class TestFormMetaclass(ReflectiveFormMetaclass):
                reflection_url = "Not a URL"

            class TestForm(forms.Form, metaclass=TestFormMetaclass):
                skipped = forms.CharField(max_length=128, label="w00t")

            self.assertTrue("test" in TestForm.base_fields)
            self.assertTrue("skipped" in TestForm.base_fields)

            field = TestForm.base_fields["test"]
            self.assertEqual(field.label, "Test")
            self.assertEqual(field.required, True)
            self.assertEqual(field.widget.is_required, True)
            self.assertIsInstance(field, forms.IntegerField)
            self.assertIsInstance(field.widget, forms.widgets.NumberInput)

            field = TestForm.base_fields["skipped"]
            self.assertEqual(field.label, "w00t")
            self.assertEqual(field.required, True)
            self.assertEqual(field.widget.is_required, True)
            self.assertIsInstance(field, forms.CharField)
            self.assertIsInstance(field.widget, forms.widgets.TextInput)

    def _test_field_creation(self, update):

        schema = {
            "label": "Test",
            "read_only": False,
            "required": True
        }
        schema.update(update)

        with mock.patch("alice.metaclasses.rabbit.get") as mock_get:

            mock_get.return_value = FakeResponse({"test": schema})

            class TestFormMetaclass(ReflectiveFormMetaclass):
                reflection_url = "Not a URL"

            class TestForm(forms.Form, metaclass=TestFormMetaclass):
                pass

            self.assertTrue("test" in TestForm.base_fields)

            field = TestForm.base_fields["test"]
            self.assertEqual(field.label, "Test")
            self.assertEqual(field.required, schema["required"])
            self.assertEqual(field.widget.is_required, schema["required"])

        return field

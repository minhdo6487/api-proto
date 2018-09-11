from django.test import Client
import unittest

from core.user.models import User


class UserApiTest(unittest.TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_validate(self):
        response = self.client.post('/api/register/')

        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 400)

    def test_register_user(self):
        payload = {
            'username'             : 'ph2@gc24.test',
            'password'             : 'pwd123457',
            'password_confirmation': 'pwd123457',
            'email'                : "ph2@localbox.lan",
            'first_name'           : 'Phuong',
            'last_name'            : 'Huynh'
        }
        response = self.client.post('/api/register/', data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username=payload['username']).count(), 1)


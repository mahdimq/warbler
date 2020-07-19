"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser.id = 1111
        db.session.commit()

        self.testuser_message = Message(text="User_test_message", user_id=self.testuser.id)
        db.session.add(self.testuser_message)
        db.session.commit()
        self.MSG = "MSG" #<-- add msg to session

    def test_authorized_addmessage(self):
        """Can user add a message?"""
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            res = client.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(res.status_code, 302)

            msg = Message.query.filter(Message.text == 'Hello').first()
            self.assertEqual(msg.text, "Hello")


    def test_authorized_showmessage(self):
        """Show messages from authorized users"""
        # Make Sample Mesage
        msg = Message(
            id=1234,
            text="a test message",
            user_id=self.testuser.id
        )
        # Add message to DB
        db.session.add(msg)
        db.session.commit()

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Retreive msg from DB
            msg = Message.query.get(1234)
            res = client.get(f'/messages/{msg.id}')
            # confirm status code and data
            self.assertEqual(res.status_code, 200)
            self.assertIn(msg.text, str(res.data))


    def test_unauthorized_showmessage(self):
        """Show messages from unauthorized user"""
         # make a client and session block
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
                sess[self.MSG] =self.testuser_message.id

            # Get messages from view route
            res = client.get(f"/messages/{self.testuser_message.id}")
            html = res.get_data(as_text=True)
            # confirm stats code and data
            self.assertEqual(res.status_code, 200)
            self.assertIn(f'<p class="single-message">{self.testuser_message.text}</p>', html)


    def test_authorized_messagedelete(self):
        """Show deleted messages route from authorzied user"""
        # Create fake unauthorized user
        fakeUser = User.signup(username="unauthorized-user",
                        email="testtest@test.com",
                        password="password",
                        image_url=None)
        fakeUser.id = 4455

        # authorized user message
        msg = Message(
            id=1234,
            text="test users message",
            user_id=self.testuser.id
        )
        # Add both messages to DB.
        db.session.add_all([fakeUser, msg])
        db.session.commit()

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = fakeUser.id #<-- unauthorized user in session
            # Unauthorized user trying to delete authorized user msg
            res = client.post("/messages/1234/delete", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn("Access unauthorized", str(res.data))
            # Check is message was deleted, and confirm msg contains data
            msg = Message.query.get(1234)
            self.assertIsNotNone(msg)

    def test_unauthorized_messagedelete(self):
        """Show unauthorized user delete msg"""
        with self.client as client: #<-- Client not in session
            # Sending post to delete and returns 'unauthorized msg'
            res = client.post(f"/messages/1234/delete")
            self.assertEqual(res.status_code, 404)
            self.assertIn("Access unauthorized", str(res.data))

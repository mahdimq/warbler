"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ["DATABASE_URL"] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class MessageModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        """Create test client, add sample data."""
        self.u1 = User.signup(
                email="u1@test.com",
                username="testuser1",
                password="password",
                image_url = None
            )
        self.u2 = User.signup(
                email="u2t@test.com",
                username="testuser2",
                password="password",
                image_url = None
            )
        db.session.commit()
        self.client = app.test_client()

    def teardown(self):
        """Clean up after each test"""
        db.session.rollback()

    def test_message_model(self):
        """Test message model"""
        # create new messages for both users
        msg = Message(text="Test message", user_id=self.u1.id)
        msg2 = Message(text="Test message", user_id=self.u2.id)
        db.session.add_all([msg,msg2])
        db.session.commit()

        self.assertEqual(len(self.u1.messages), 1) #<-- check length of list == 1
        self.assertIn(msg, self.u1.messages) #<-- check is there is data in msgs
        self.assertEqual(self.u1.messages[0].text, "Test message") #<-- show msg text
        self.assertIn(msg2, self.u2.messages) #<-- check is there is data in msgs
        self.assertEqual(len(self.u2.messages), 1) #<-- check length of list == 1
        self.assertEqual(self.u2.messages[0].text, "Test message") #<-- show msg text


    def test_addmessage(self):
        """Check to see if messages can be added"""
        # create new messages for both users
        msg = Message(text='Test message', user_id=self.u1.id)
        msg2 = Message(text='Test message', user_id=self.u2.id)
        db.session.commit()

        # add messages
        self.u1.messages.append(msg) #<-- Add message to messages
        self.u2.messages.append(msg2) #<-- Add message to messages
        self.assertIn(msg, self.u1.messages) #<-- show is data exists in messages
        self.assertIn(msg2, self.u2.messages) #<-- show is data exists in messages

    def test_likemessage(self):
        """Check to see if messages can be likes"""
        # create new messages for both users
        msg = Message(text='Test message', user_id=self.u1.id)
        msg2 = Message(text='Test message', user_id=self.u2.id)
        db.session.commit()

        # add to liked messages
        self.u1.likes.append(msg2) #<-- Add msg to likes
        self.u2.likes.append(msg) #<-- Add msg to likes
        self.assertIn(msg2, self.u1.likes) #<-- show if message in likes
        self.assertIn(msg, self.u2.likes) #<-- show if message in likes

        # remove from likes messages
        self.u1.likes.remove(msg2) #<-- Remove msg from likes
        self.u2.likes.remove(msg) #<-- Remove msg from likes
        self.assertNotIn(msg2, self.u1.likes) #<-- show NONE is msg not in likes
        self.assertNotIn(msg, self.u2.likes) #<-- show NONE is msg not in likes

    # def test_deletemessage(self):
    #     """Check to see if messages can be deleted"""
    #     msg = Message(text='Test message', user_id=self.u1.id)
    #     msg2 = Message(text='Test message', user_id=self.u2.id)
    #     db.session.commit()

    #     self.u1.messages.append(msg)
    #     self.u2.messages.append(msg2)

    #     self.assertIn(msg, self.u1.messages)
    #     self.u1.messages.remove(msg)
    #     self.assertNotIn(msg, self.u1.messages)

    #     self.assertIn(msg2, self.u2.messages)
    #     self.u2.messages.remove(msg2)
    #     self.assertNotIn(msg2, self.u2.messages)

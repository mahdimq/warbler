"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError

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


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

        # Create Users
        self.u1 = User.signup(
            email="TestEmail1",
            username="TestUsername1",
            image_url=None,
            password="TestPassword1",
        )
        self.u1_id = 1111
        self.u1.id = self.u1_id

        self.u2 = User.signup(
            email="TestEmail2",
            username="TestUsername2",
            image_url=None,
            password="TestPassword2",
        )
        self.u2_id = 2222
        self.u2.id = self.u2_id

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_user_model(self):
        """Does basic model work?"""

        u = User(email="test@test.com", username="testuser", password="HASHED_PASSWORD")

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    def test_user_follows(self):
        """Check user follow model"""
        # user 1 following user 2
        self.u1.following.append(self.u2)
        db.session.commit()

        # check if user 2 is following (following list = 0)
        self.assertEqual(len(self.u2.following), 0)
        # check if user 1 is following (following list = 1)
        self.assertEqual(len(self.u1.following), 1)
        # check if user 2 is being followed (followed list = 1)
        self.assertEqual(len(self.u2.followers), 1)
        # check if user 1 is being followed (followed list = 0)
        self.assertEqual(len(self.u1.followers), 0)

        # checks that user 2 has one follower, user 1
        self.assertEqual(self.u2.followers[0].id, self.u1.id)
        # checks that user 1 is following one user, user 2
        self.assertEqual(self.u1.following[0].id, self.u2.id)

    def test_is_following(self):
        # user 1 following user 2
        self.u1.following.append(self.u2)
        db.session.commit()

        # check if user 1 is following user 2
        self.assertTrue(self.u1.is_following(self.u2))
        # check if user 2 is NOT following user 1
        self.assertFalse(self.u2.is_following(self.u1))

    def test_is_followed_by(self):
        # user 1 following user 2
        self.u1.following.append(self.u2)
        db.session.commit()

        # check if user 2 is being followed by user 1
        self.assertTrue(self.u2.is_followed_by(self.u1))
        # check if user 1 is NOT being followed by user 2
        self.assertFalse(self.u1.is_followed_by(self.u2))

# ========================================================================= #

    def test_valid_signup(self):
        # find user from DB
        user_test = User.query.filter_by(username=self.u1.username).first()
        # confirm user is available
        self.assertIsNotNone(user_test)
        # confirm username matches created user
        self.assertEqual(user_test.username, "TestUsername1")
        # confirm email matches created email
        self.assertEqual(user_test.email, "TestEmail1")
        # confirm password is NOT the entered password
        self.assertNotEqual(user_test.password, "jibberish")
        # Bcrypt strings should start with $2b$
        self.assertTrue(user_test.password.startswith("$2b$"))

    def test_invalid_username_signup(self):
        wrong_username = User.signup("username", None, "something", None)
        user_id = 11001101
        wrong_username.id = user_id
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_invalid_email_signup(self):
        wrong_email = User.signup("username", None, "password", None)
        user_id = 11001101
        wrong_email.id = user_id
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_invalid_password_signup(self):
        with self.assertRaises(ValueError):
            User.signup("username", "bob@bob.com", None, None)

        with self.assertRaises(ValueError):
            User.signup("username", "bob@bob.com", None, None)

# ========================================================================= #

    def test_valid_authentication(self):
        # Get user info from DB
        user = User.query.get(self.u1_id)
        # Create user with username and password
        authenticated = User.authenticate(self.u1.username, "TestPassword1")
        # confirm user exists by checking is is NOT NONE
        self.assertIsNotNone(authenticated)
        # check if user id created equals original user id
        self.assertEqual(user, authenticated)

    def test_invalid_username(self):
        self.assertFalse(User.authenticate("badusername", "password"))

    def test_wrong_password(self):
        self.assertFalse(User.authenticate(self.u1.username, "badpassword"))

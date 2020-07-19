"""User Views tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py

import os
from unittest import TestCase
from models import db, connect_db, User, Message, Follows
from app import app, CURR_USER_KEY, g

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

app.config["WTF_CSRF_ENABLED"] = False


class UserViewsTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

        # Create test users
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

        self.u3 = User.signup(
            email="TestEmail3",
            username="TestUsername3",
            image_url=None,
            password="TestPassword3",
            )
        self.u3_id = 3333
        self.u3.id = self.u3_id

        db.session.commit()

        # Setup followers
        f1 = self.u1.following.append(self.u2)
        f2 = self.u2.following.append(self.u1)
        f3 = self.u3.following.append(self.u1)

        db.session.commit()

        # Setup test message
        self.msg = Message(id=0000, text='Test Message', user_id=self.u2.id)
        db.session.add(self.msg)
        db.session.commit()

        self.MSG = "MSG"

    def tearDown(self):
        """Clean up any fouled transaction."""

        db.session.rollback()

    def test_signup(self):
        """Test Sign Up root route"""
        with self.client as client:
            res = client.get('/')
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn("<h1>What's Happening?</h1>", html)
            self.assertIn("<h4>New to Warbler?</h4>", html)


    def test_login(self):
        """Check login route"""
        with self.client as client:
            # testing a get request
            res = client.get('/login')
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn('<h2 class="join-message">Welcome back.</h2>', html)


    def test_logout(self):
        """Check logout route"""
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            res = client.get("/logout")
            self.assertEqual(res.status_code, 302)
            self.assertEqual(res.location, 'http://localhost/')


    def test_show_users(self):
        """Check show users route"""
        with self.client as client:
            res = client.get("/users")

            self.assertIn("@TestUsername1", str(res.data))
            self.assertIn("@TestUsername2", str(res.data))

    def test_show_user_detail(self):
        """Check user detail route"""
        with self.client as client:
            res = client.get(f"/users/{self.u1_id}")
            html = res.get_data(as_text=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn("@TestUsername1", str(res.data))

    def test_show_user_following(self):
        """Check user following route"""
        # user in session
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            res = client.get(f"/users/{self.u1_id}/followers")
            self.assertEqual(res.status_code, 200)
            self.assertIn("@TestUsername1", str(res.data))

        # user not in session
        with self.client as client:
            res = client.get(f"users/{self.u1_id}/followers")
            self.assertLessEqual(res.status_code, 302)
            self.assertIn("@TestUsername1", str(res.data))

    def test_show_user_followers(self):
        """Check user followers route"""
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id
            res = client.get(f'users/{self.u1_id}/followers')

            self.assertEqual(res.status_code, 200)
            self.assertIn("@TestUsername1", str(res.data))


    def test_show_follow_user(self):
        """Check route when you follow a user"""
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id
            res = client.post(f'users/follow/{self.u1.id}')

            # test with user in session
            self.assertEqual(res.status_code, 302)
            self.assertEqual(res.location, f'http://localhost/users/{self.u1_id}/following')

            # test with no user in session
            res = client.post(f'users/follow/{self.u1.id}')
            with client.session_transaction() as sess:
                flash = dict(sess['_flashes']).get('danger')

    def test_show_add_like(self):
        """Show route when message is likes"""
        with self.client as client:
            id = self.msg.id
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            res = client.post("/messages/0000/like", follow_redirects=True)
            self.assertEqual(res.status_code, 200)

    def test_show_remove_like(self):
        """Show route when message is disliked"""
        # Get message from DB
        msg = Message.query.filter(Message.text=="Test Message").one()
        self.assertIsNotNone(msg)
        self.assertNotEqual(msg.user_id, self.u1_id)

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = client.post(f"/messages/{msg.id}/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

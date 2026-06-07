import unittest
import requests
import random

BASE_URL = "http://localhost:8000/api"

class ChatHistoryE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a new user for history tests
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"history_user_{cls.rand_id}@example.com"
        cls.password = "historypassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_conversations_flow(self):
        # 1. Verify list of sessions is initially empty
        sessions_resp = requests.get(f"{BASE_URL}/conversations/sessions", headers=self.headers)
        self.assertEqual(sessions_resp.status_code, 200)
        self.assertEqual(len(sessions_resp.json()), 0, "Expected empty session list on startup")

        # 2. Trigger first chat query (this will auto-create a session)
        chat_resp_1 = requests.post(
            f"{BASE_URL}/chat",
            json={"question": "Hello DocumentIQ Assistant!"},
            headers=self.headers
        )
        self.assertEqual(chat_resp_1.status_code, 200)
        chat_data_1 = chat_resp_1.json()
        self.assertIn("session_id", chat_data_1)
        session_id = chat_data_1["session_id"]
        self.assertIsNotNone(session_id)

        # 3. Trigger second chat query in the same session
        chat_resp_2 = requests.post(
            f"{BASE_URL}/chat",
            json={"question": "How do you help me?", "session_id": session_id},
            headers=self.headers
        )
        self.assertEqual(chat_resp_2.status_code, 200)
        chat_data_2 = chat_resp_2.json()
        self.assertEqual(chat_data_2["session_id"], session_id, "Session ID should match the passed one")

        # 4. Verify conversation is listed in sessions
        sessions_resp_2 = requests.get(f"{BASE_URL}/conversations/sessions", headers=self.headers)
        self.assertEqual(sessions_resp_2.status_code, 200)
        sessions = sessions_resp_2.json()
        self.assertEqual(len(sessions), 1, "Expected exactly 1 session to be created")
        self.assertEqual(sessions[0]["id"], session_id)
        self.assertIn("Hello", sessions[0]["title"])

        # 5. Fetch message history and verify prompts/responses
        history_resp = requests.get(f"{BASE_URL}/conversations/sessions/{session_id}/messages", headers=self.headers)
        self.assertEqual(history_resp.status_code, 200)
        messages = history_resp.json()
        
        # We expect 4 messages: 2 from user, 2 from bot
        self.assertEqual(len(messages), 4, f"Expected 4 messages, got {len(messages)}")
        
        self.assertEqual(messages[0]["sender"], "user")
        self.assertEqual(messages[0]["text"], "Hello DocumentIQ Assistant!")
        self.assertEqual(messages[1]["sender"], "bot")
        self.assertEqual(messages[1]["text"], chat_data_1["answer"])
        
        self.assertEqual(messages[2]["sender"], "user")
        self.assertEqual(messages[2]["text"], "How do you help me?")
        self.assertEqual(messages[3]["sender"], "bot")
        self.assertEqual(messages[3]["text"], chat_data_2["answer"])

        # 6. Rename session title
        rename_title = "DocumentIQ Overview Discussion"
        rename_resp = requests.put(
            f"{BASE_URL}/conversations/sessions/{session_id}",
            json={"title": rename_title},
            headers=self.headers
        )
        self.assertEqual(rename_resp.status_code, 200)
        self.assertEqual(rename_resp.json()["title"], rename_title)

        # Confirm rename is visible in sessions list
        sessions_resp_3 = requests.get(f"{BASE_URL}/conversations/sessions", headers=self.headers)
        self.assertEqual(sessions_resp_3.json()[0]["title"], rename_title)

        # 7. Delete session
        delete_resp = requests.delete(f"{BASE_URL}/conversations/sessions/{session_id}", headers=self.headers)
        self.assertEqual(delete_resp.status_code, 204)

        # Confirm session is deleted and empty list is returned
        sessions_resp_4 = requests.get(f"{BASE_URL}/conversations/sessions", headers=self.headers)
        self.assertEqual(len(sessions_resp_4.json()), 0)

if __name__ == "__main__":
    unittest.main()

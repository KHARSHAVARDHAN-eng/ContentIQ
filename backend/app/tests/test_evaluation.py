import unittest
import requests
import time
import random
import sqlite3

BASE_URL = "http://localhost:8000/api"

class EvaluationDashboardE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a new user to isolate evaluations data
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"eval_user_{cls.rand_id}@example.com"
        cls.password = "evalpassword123"
        
        # Register and Login
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}
        cls.user_id = login_resp.json().get("user_id") # Wait, if user_id is returned? Let's check token subject.
        
    def test_eval_logging_and_telemetry(self):
        # 1. Trigger a chat request which should automatically log a RAG event in DB
        chat_url = f"{BASE_URL}/chat"
        question = "What is the capital of France?"
        
        print("Sending chat request (will auto-log evaluation)...")
        chat_resp = requests.post(chat_url, json={"question": question}, headers=self.headers)
        self.assertEqual(chat_resp.status_code, 200)
        chat_data = chat_resp.json()
        self.assertIn("answer", chat_data)

        # Allow DB write and metric generation to complete
        time.sleep(1)

        # 2. Query evaluations logs API endpoint to verify it is logged
        logs_url = f"{BASE_URL}/evaluations/logs"
        logs_resp = requests.get(logs_url, headers=self.headers)
        self.assertEqual(logs_resp.status_code, 200)
        logs = logs_resp.json()
        
        self.assertGreater(len(logs), 0, "No evaluation logs were recorded")
        
        last_log = logs[0]
        self.assertEqual(last_log["query"], question)
        self.assertEqual(last_log["answer"], chat_data["answer"])
        self.assertGreaterEqual(last_log["latency_ms"], 0)
        self.assertEqual(last_log["user_feedback"], 0) # Initially unrated
        self.assertIsNotNone(last_log["faithfulness_score"])
        self.assertIsNotNone(last_log["answer_relevance_score"])
        
        log_id = last_log["id"]
        
        # 3. Test submitting user feedback (thumbs up)
        feedback_url = f"{BASE_URL}/evaluations/{log_id}/feedback"
        feedback_resp = requests.post(feedback_url, json={"feedback": 1}, headers=self.headers)
        self.assertEqual(feedback_resp.status_code, 200)
        self.assertEqual(feedback_resp.json()["user_feedback"], 1)

        # Verify feedback change reflected in log list
        logs_resp_2 = requests.get(logs_url, headers=self.headers)
        self.assertEqual(logs_resp_2.json()[0]["user_feedback"], 1)

        # 4. Verify aggregate stats endpoint
        stats_url = f"{BASE_URL}/evaluations/stats"
        stats_resp = requests.get(stats_url, headers=self.headers)
        self.assertEqual(stats_resp.status_code, 200)
        stats_data = stats_resp.json()
        
        self.assertEqual(stats_data["total_queries"], 1)
        self.assertEqual(stats_data["thumbs_up_count"], 1)
        self.assertEqual(stats_data["thumbs_down_count"], 0)
        self.assertEqual(stats_data["positive_feedback_pct"], 100.0)
        self.assertGreaterEqual(stats_data["avg_latency_ms"], 0.0)
        self.assertGreater(len(stats_data["daily_metrics"]), 0)
        
        print("Aggregate stats verification passed:", stats_data)

if __name__ == "__main__":
    unittest.main()

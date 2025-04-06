import mysql.connector
from db_config import get_db_config
from datetime import datetime

class Database:
    def __init__(self):
        db_config = get_db_config()
        self.conn = mysql.connector.connect(**db_config)
        self.cursor = self.conn.cursor(dictionary=True)

    def user_exists(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        return self.cursor.fetchone() is not None

    def add_user(self, user_id, username, password):
        self.cursor.execute("""
            INSERT INTO users (user_id, username, password, is_notif_active)
            VALUES (%s, %s, %s, 0)
            ON DUPLICATE KEY UPDATE username=%s, password=%s
        """, (user_id, username, password, username, password))
        self.conn.commit()

    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        return self.cursor.fetchone()

    def set_notif_status(self, user_id, status):
        self.cursor.execute("UPDATE users SET is_notif_active = %s WHERE user_id = %s", (int(status), user_id))
        self.conn.commit()

    def get_deadlines(self, user_id):
        self.cursor.execute("""
            SELECT summary AS title, description, end_time AS date 
            FROM calendar 
            WHERE user_id = %s AND is_completed = 0 
            ORDER BY end_time ASC
        """, (user_id,))
        return self.cursor.fetchall()

    def delete_expired_events(self):
        self.cursor.execute("DELETE FROM calendar WHERE end_time < NOW()")
        self.conn.commit()

    def get_all_users(self):
        self.cursor.execute("SELECT user_id FROM users")
        return [row['user_id'] for row in self.cursor.fetchall()]

    def get_upcoming_events(self, user_id):
        self.cursor.execute("""
            SELECT uid, summary, end_time 
            FROM calendar 
            WHERE user_id = %s AND is_completed = 0
        """, (user_id,))
        return self.cursor.fetchall()

    def is_notified(self, user_id, uid, delta):
        self.cursor.execute("""
            SELECT * FROM notification_log 
            WHERE user_id = %s AND uid = %s AND delta_time = %s
        """, (user_id, uid, str(delta)))
        return self.cursor.fetchone() is not None

    def mark_as_notified(self, user_id, uid, delta):
        self.cursor.execute("""
            INSERT INTO notification_log (user_id, uid, delta_time) 
            VALUES (%s, %s, %s)
        """, (user_id, uid, str(delta)))
        self.conn.commit()

    def mark_completed(self, user_id, uid):
        self.cursor.execute("""
            UPDATE calendar SET is_completed = 1 
            WHERE user_id = %s AND uid = %s
        """, (user_id, uid))
        self.conn.commit()

    def delete_user(self, user_id):
        self.cursor.execute("DELETE FROM calendar WHERE user_id = %s", (user_id,))
        self.cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        self.conn.commit()
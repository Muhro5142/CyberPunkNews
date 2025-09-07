import sqlite3

database = "db.db"


    

class ManagerDB:
    def __init__(self, db):
        self.conn = sqlite3.connect(db)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, 
                name TEXT CHECK(length(name) <= 20) UNIQUE, 
                email TEXT CHECK(length(email) <= 20) UNIQUE, 
                password TEXT CHECK(length(password) <= 20)
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS news(
            id INTEGER PRIMARY KEY,
            userid INTEGER,
            russian TEXT,
            english TEXT,
            FOREIGN KEY (userid) REFERENCES users(id)
            );
        """)
        self.conn.commit()

    def fetchuser(self):
        self.cursor.execute("SELECT * FROM users")
        rows = self.cursor.fetchall()
        return rows
    
    def fetchuserbyid(self, id):
        self.cursor.execute("SELECT * FROM users WHERE id=?", (id,))
        rows = self.cursor.fetchall()
        return rows

    def usersearch(self, email):
        self.cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        rows = self.cursor.fetchall()
        return rows

    def insertuser(self, name, email, password):
        self.cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        self.conn.commit()

    def removeuser(self, id):
        self.cursor.execute("DELETE FROM users WHERE id=?", (id,))
        self.conn.commit()

    def updateuser(self, id, name, email, password):
        self.cursor.execute("UPDATE users SET name = ?, email = ?, password = ? WHERE id = ?", (name, email, password, id))
        self.conn.commit()

    def fetchnews(self):
        self.cursor.execute("SELECT * FROM news")
        rows = self.cursor.fetchall()
        return rows

    def insertnews(self, userid, russian, english):
        self.cursor.execute("INSERT INTO news (userid, russian, english) VALUES (?, ?, ?)", (userid, russian, english))
        self.conn.commit()

    def removenews(self, id):
        self.cursor.execute("DELETE FROM news WHERE id=?", (id,))
        self.conn.commit()

    def updatenews(self, id, userid, russian, english):
        self.cursor.execute("UPDATE news SET userid = ?, russian = ?, english = ? WHERE id = ?", (userid, russian, english, id))
        self.conn.commit()




    def __del__(self):
        self.conn.close()
if __name__ == "__main__":
    db = ManagerDB(database)
    db.insertuser("John", "john@exmple.com" , "john123")

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt
from db_connection import get_db_connection

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin přihlášení")
        self.setFixedSize(450, 320)
        self.setStyleSheet("background-color: #f5f6fa; color: #2f3640;")

        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(50, 40, 50, 40)

        # Nadpis
        title = QLabel("Admin přihlášení")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #e84118; margin-bottom: 20px;")
        main_layout.addWidget(title)

        # Uživatelské jméno
        self.username = QLineEdit()
        self.username.setPlaceholderText("Uživatelské jméno")
        self.username.setFixedHeight(45)
        self.username.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background: #ffffff;
                font-size: 15px;
                color: #2f3640;
            }
            QLineEdit:focus {
                border: 1px solid #4bcffa;
            }
        """)
        main_layout.addWidget(self.username)

        # Heslo
        self.password = QLineEdit()
        self.password.setPlaceholderText("Heslo")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFixedHeight(45)
        self.password.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background: #ffffff;
                font-size: 15px;
                color: #2f3640;
            }
            QLineEdit:focus {
                border: 1px solid #4bcffa;
            }
        """)
        main_layout.addWidget(self.password)

        # Spacer
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Tlačítko
        login_btn = QPushButton("Přihlásit se")
        login_btn.setFixedHeight(50)
        login_btn.setStyleSheet("""
            QPushButton {
                background: #4bcffa;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0fbcf9;
            }
            QPushButton:pressed {
                background: #01a3d9;
            }
        """)
        login_btn.clicked.connect(self.check_login)
        main_layout.addWidget(login_btn)

        self.setLayout(main_layout)

    def check_login(self):
        u = self.username.text().strip()
        p = self.password.text().strip()

        if not u or not p:
            QMessageBox.warning(self, "Chyba", "Vyplňte uživatelské jméno i heslo.")
            return

        # --- Napojení na databázi ---
        conn = get_db_connection()
        if not conn:
            QMessageBox.critical(self, "Chyba", "Nepodařilo se připojit k databázi.")
            return

        try:
            cursor = conn.cursor(dictionary=True)
            # Dotaz do databáze
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (u, p))
            admin = cursor.fetchone()

            if admin:
                self.accept()  # Přihlášení úspěšné, okno se zavře a pustí tě dál
            else:
                QMessageBox.warning(self, "Chyba", "Špatné přihlašovací údaje.")
                self.password.clear() # Vymaže špatné heslo
        except Exception as e:
            QMessageBox.critical(self, "Chyba databáze", str(e))
        finally:
            cursor.close()
            conn.close()

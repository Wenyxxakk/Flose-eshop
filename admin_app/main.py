# admin_app/main.py
import sys
from PyQt5.QtWidgets import QApplication
from login_window import LoginWindow
from main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)

    login = LoginWindow()
    result = login.exec_()

    if result == LoginWindow.Accepted:
        main_window = MainWindow()
        main_window.show()
        main_window.raise_()
        main_window.activateWindow()

    sys.exit(app.exec_())

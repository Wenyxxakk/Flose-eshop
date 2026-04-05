import re
import csv
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QHBoxLayout, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QTextEdit, QMessageBox, QCheckBox, QDateEdit, QComboBox,
    QFileDialog
)
from PyQt5.QtCore import Qt, QDate
from db_connection import get_db_connection

# ─── VELMI JEDNODUCHÝ A ČISTÝ STYL ───
MAIN_STYLE = """
    QMainWindow { background-color: #f5f6fa; color: #2f3640; }
    QLabel { color: #2f3640; font-weight: bold; font-size: 18px; }
    QTabWidget::pane { border: 1px solid #dcdde1; background: #ffffff; border-radius: 4px; }
    QTabBar::tab { background: #e84118; color: #ffffff; padding: 10px 25px; font-size: 14px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
    QTabBar::tab:!selected { background: #dcdde1; color: #7f8fa6; }
    QTableWidget { background-color: #ffffff; gridline-color: #f5f6fa; color: #2f3640; font-size: 14px; border: none; }
    QHeaderView::section { background-color: #f5f6fa; color: #7f8fa6; padding: 10px; border: none; font-weight: bold; border-bottom: 2px solid #dcdde1; }
    QPushButton { background: #4bcffa; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; font-size: 14px; }
    QPushButton:hover { background: #0fbcf9; }
    QLineEdit, QTextEdit, QDoubleSpinBox, QSpinBox, QDateEdit, QComboBox { background: #ffffff; color: #2f3640; border: 1px solid #dcdde1; padding: 8px; border-radius: 4px; }
    QLineEdit:focus, QTextEdit:focus, QDoubleSpinBox:focus { border: 1px solid #4bcffa; }
"""


# ─── ZÁLOŽKA: PRODUKTY ───
class ProductsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_products()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Správa produktů")
        title.setStyleSheet("color: #e84118; font-size: 24px;")
        layout.addWidget(title)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(7)
        self.products_table.setHorizontalHeaderLabels(
            ["ID", "Název", "Cena", "Skladem", "Sleva (%)", "Obrázek", "Akce"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.verticalHeader().setDefaultSectionSize(50)
        layout.addWidget(self.products_table)

        btn_layout = QHBoxLayout()

        add_btn = QPushButton("Přidat produkt")
        add_btn.clicked.connect(self.show_add_product_dialog)
        btn_layout.addWidget(add_btn)

        # NOVÉ TLAČÍTKO PRO IMPORT
        import_btn = QPushButton("Importovat CSV")
        import_btn.setStyleSheet("background-color: #2bcbba;")
        import_btn.clicked.connect(self.import_from_csv)
        btn_layout.addWidget(import_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_products(self):
        conn = get_db_connection()
        if not conn: return

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, price, stock, discount_percent, image_url FROM products")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        self.products_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.products_table.setItem(row_idx, 0, QTableWidgetItem(str(row['id'])))
            self.products_table.setItem(row_idx, 1, QTableWidgetItem(row['name'] or ""))
            self.products_table.setItem(row_idx, 2, QTableWidgetItem(
                f"{float(row['price']):.2f} Kč" if row['price'] else "0.00 Kč"))
            self.products_table.setItem(row_idx, 3, QTableWidgetItem(str(row['stock'] or 0)))

            discount_val = row.get('discount_percent') or 0
            discount_text = f"{discount_val} %" if discount_val > 0 else "-"
            self.products_table.setItem(row_idx, 4, QTableWidgetItem(discount_text))

            self.products_table.setItem(row_idx, 5, QTableWidgetItem(row['image_url'] or "žádný"))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)

            edit_btn = QPushButton("Upravit")
            edit_btn.setStyleSheet("background-color: #7f8fa6;")
            edit_btn.clicked.connect(lambda _, rid=row['id']: self.show_edit_product_dialog(rid))

            delete_btn = QPushButton("Smazat")
            delete_btn.setStyleSheet("background-color: #ff3f34;")
            delete_btn.clicked.connect(lambda _, rid=row['id']: self.delete_product(rid))

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.products_table.setCellWidget(row_idx, 6, actions_widget)

    def import_from_csv(self):
        # 1. Otevře okno pro výběr souboru
        file_path, _ = QFileDialog.getOpenFileName(self, "Vyberte CSV soubor", "", "CSV Files (*.csv);;All Files (*)")

        if not file_path:
            return  # Uživatel okno zavřel

        conn = get_db_connection()
        if not conn: return
        cursor = conn.cursor()

        try:
            # Použito utf-8-sig kvůli Excelu
            with open(file_path, mode='r', encoding='utf-8-sig') as file:
                csv_reader = csv.DictReader(file)

                count = 0
                for row in csv_reader:
                    raw_name = row.get('name', '')
                    if not raw_name: continue

                    # ČIŠTĚNÍ NÁZVU (odstranění pomlček, lomítek a duplicit)
                    clean_name = re.sub(r'[-/]', ' ', raw_name)
                    words = clean_name.split()
                    unique_words = []
                    seen = set()
                    for w in words:
                        if w.lower() not in seen:
                            seen.add(w.lower())
                            unique_words.append(w)
                    final_name = " ".join(unique_words).strip()

                    # Bezpečné načtení číselných hodnot
                    try:
                        price = float(row.get('price', 0) or 0)
                    except ValueError:
                        price = 0.0

                    try:
                        stock = int(row.get('stock', 0) or 0)
                    except ValueError:
                        stock = 0

                    try:
                        discount = int(row.get('discount_percent', 0) or 0)
                    except ValueError:
                        discount = 0

                    image_url = row.get('image_url', '').strip() or None
                    description = row.get('description', '').strip() or None

                    cursor.execute(
                        "INSERT INTO products (name, price, stock, discount_percent, image_url, description) VALUES (%s, %s, %s, %s, %s, %s)",
                        (final_name, price, stock, discount, image_url, description)
                    )
                    count += 1

            conn.commit()
            QMessageBox.information(self, "Hotovo", f"Úspěšně importováno {count} produktů!")
            self.load_products()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Chyba importu",
                                 f"Zkontrolujte formát CSV souboru.\nNázvy sloupců musí být: name, price, stock, discount_percent, image_url, description\n\nDetail: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def show_add_product_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Přidat produkt")
        dialog.resize(450, 500)
        layout = QFormLayout(dialog)

        name = QLineEdit()

        price = QDoubleSpinBox()
        price.setRange(0, 100000)
        price.setDecimals(2)

        stock = QSpinBox()
        stock.setRange(0, 10000)

        discount = QSpinBox()
        discount.setRange(0, 100)
        discount.setSuffix(" %")

        image_url = QLineEdit()
        description = QTextEdit()

        layout.addRow("Název:", name)
        layout.addRow("Cena (Kč):", price)
        layout.addRow("Sleva (%):", discount)
        layout.addRow("Skladem:", stock)
        layout.addRow("URL obrázku:", image_url)
        layout.addRow("Popis:", description)

        save_btn = QPushButton("Uložit")
        save_btn.clicked.connect(lambda: self.save_product(
            name.text(), price.value(), stock.value(), discount.value(),
            image_url.text(), description.toPlainText(), dialog, is_edit=False
        ))
        layout.addRow(save_btn)
        dialog.exec_()

    def show_edit_product_dialog(self, product_id):
        conn = get_db_connection()
        if not conn: return
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
        cursor.close()
        conn.close()

        if not product: return

        dialog = QDialog(self)
        dialog.setWindowTitle("Upravit produkt")
        dialog.resize(450, 500)
        layout = QFormLayout(dialog)

        name = QLineEdit(product['name'])

        price = QDoubleSpinBox()
        price.setRange(0, 100000)
        price.setDecimals(2)
        price.setValue(float(product['price']))

        stock = QSpinBox()
        stock.setRange(0, 10000)
        stock.setValue(product['stock'])

        discount = QSpinBox()
        discount.setRange(0, 100)
        discount.setSuffix(" %")
        discount.setValue(product.get('discount_percent', 0) or 0)

        image_url = QLineEdit(product['image_url'] or "")
        description = QTextEdit(product['description'] or "")

        layout.addRow("Název:", name)
        layout.addRow("Cena (Kč):", price)
        layout.addRow("Sleva (%):", discount)
        layout.addRow("Skladem:", stock)
        layout.addRow("URL obrázku:", image_url)
        layout.addRow("Popis:", description)

        save_btn = QPushButton("Uložit změny")
        save_btn.clicked.connect(lambda: self.save_product(
            name.text(), price.value(), stock.value(), discount.value(),
            image_url.text(), description.toPlainText(), dialog, is_edit=True, product_id=product_id
        ))
        layout.addRow(save_btn)
        dialog.exec_()

    def save_product(self, name, price, stock, discount_percent, image_url, description, dialog, is_edit=False,
                     product_id=None):
        if not name:
            QMessageBox.warning(self, "Chyba", "Název je povinný.")
            return

        name = re.sub(r'[-/]', ' ', name)
        words = name.split()
        clean_words = []
        seen = set()
        for w in words:
            if w.lower() not in seen:
                seen.add(w.lower())
                clean_words.append(w)
        clean_name = " ".join(clean_words).strip()

        conn = get_db_connection()
        if not conn: return
        cursor = conn.cursor()
        try:
            if is_edit:
                cursor.execute(
                    "UPDATE products SET name = %s, price = %s, stock = %s, discount_percent = %s, image_url = %s, description = %s WHERE id = %s",
                    (clean_name, price, stock, discount_percent, image_url or None, description or None, product_id))
            else:
                cursor.execute(
                    "INSERT INTO products (name, price, stock, discount_percent, image_url, description) VALUES (%s, %s, %s, %s, %s, %s)",
                    (clean_name, price, stock, discount_percent, image_url or None, description or None))
            conn.commit()
            dialog.close()
            self.load_products()
        except Exception as e:
            QMessageBox.critical(self, "Chyba", str(e))
        finally:
            cursor.close()
            conn.close()

    def delete_product(self, product_id):
        if QMessageBox.question(self, "Potvrzení", "Opravdu smazat?") == QMessageBox.Yes:
            conn = get_db_connection()
            if not conn: return
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            conn.commit()
            cursor.close()
            conn.close()
            self.load_products()


# ─── ZÁLOŽKA: SLEVY ───
class DiscountsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_discounts()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("Správa slevových kódů")
        title.setStyleSheet("color: #e84118; font-size: 24px;")
        layout.addWidget(title)

        self.discounts_table = QTableWidget()
        self.discounts_table.setColumnCount(8)
        self.discounts_table.setHorizontalHeaderLabels(
            ["ID", "Kód", "Typ", "Hodnota", "Aktivní", "Platný do", "Max použití", "Akce"])
        self.discounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.discounts_table.verticalHeader().setDefaultSectionSize(50)
        layout.addWidget(self.discounts_table)

        add_btn = QPushButton("Přidat kód")
        add_btn.clicked.connect(self.show_add_discount_dialog)
        layout.addWidget(add_btn, alignment=Qt.AlignLeft)

    def load_discounts(self):
        conn = get_db_connection()
        if not conn: return
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM discount_codes")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        self.discounts_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.discounts_table.setItem(row_idx, 0, QTableWidgetItem(str(row['id'])))
            self.discounts_table.setItem(row_idx, 1, QTableWidgetItem(row['code']))
            self.discounts_table.setItem(row_idx, 2, QTableWidgetItem(row['discount_type']))
            self.discounts_table.setItem(row_idx, 3, QTableWidgetItem(f"{row['discount_value']:.2f}"))
            self.discounts_table.setItem(row_idx, 4, QTableWidgetItem("Ano" if row['is_active'] else "Ne"))
            self.discounts_table.setItem(row_idx, 5, QTableWidgetItem(str(row['valid_until'] or "-")))
            self.discounts_table.setItem(row_idx, 6, QTableWidgetItem(str(row['max_uses'] or "∞")))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)

            edit_btn = QPushButton("Upravit")
            edit_btn.setStyleSheet("background-color: #7f8fa6;")
            edit_btn.clicked.connect(lambda _, rid=row['id']: self.show_edit_discount_dialog(rid))

            delete_btn = QPushButton("Smazat")
            delete_btn.setStyleSheet("background-color: #ff3f34;")
            delete_btn.clicked.connect(lambda _, rid=row['id']: self.delete_discount(rid))

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.discounts_table.setCellWidget(row_idx, 7, actions_widget)

    def show_add_discount_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Přidat kód")
        layout = QFormLayout(dialog)

        code = QLineEdit()
        discount_type = QComboBox()
        discount_type.addItems(["percent", "fixed"])
        value = QDoubleSpinBox()
        value.setRange(0, 100000)
        active = QCheckBox("Aktivní")
        active.setChecked(True)
        valid_from = QDateEdit()
        valid_from.setCalendarPopup(True)
        valid_from.setDate(QDate.currentDate())
        valid_until = QDateEdit()
        valid_until.setCalendarPopup(True)
        valid_until.setDate(QDate.currentDate().addDays(30))
        max_uses = QSpinBox()
        max_uses.setRange(0, 10000)
        max_uses.setSpecialValueText("Neomezeno")

        layout.addRow("Kód:", code)
        layout.addRow("Typ:", discount_type)
        layout.addRow("Hodnota:", value)
        layout.addRow("Aktivní:", active)
        layout.addRow("Od:", valid_from)
        layout.addRow("Do:", valid_until)
        layout.addRow("Max použití:", max_uses)

        btn = QPushButton("Uložit")
        btn.clicked.connect(
            lambda: self.save_discount(code.text(), discount_type.currentText(), value.value(), active.isChecked(),
                                       valid_from.date().toString("yyyy-MM-dd"),
                                       valid_until.date().toString("yyyy-MM-dd"), max_uses.value(), dialog))
        layout.addRow(btn)
        dialog.exec_()

    def show_edit_discount_dialog(self, discount_id):
        conn = get_db_connection()
        if not conn: return
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM discount_codes WHERE id = %s", (discount_id,))
        discount = cursor.fetchone()
        cursor.close()
        conn.close()

        if not discount: return
        dialog = QDialog(self)
        layout = QFormLayout(dialog)

        code_input = QLineEdit(discount['code'])
        discount_type = QComboBox()
        discount_type.addItems(["percent", "fixed"])
        discount_type.setCurrentText(discount['discount_type'])

        value = QDoubleSpinBox()
        value.setRange(0, 100000)
        value.setValue(float(discount['discount_value']))

        active = QCheckBox("Aktivní")
        active.setChecked(discount['is_active'])
        valid_from = QDateEdit()
        valid_from.setCalendarPopup(True)
        valid_from.setDate(
            QDate.fromString(str(discount['valid_from'] or QDate.currentDate().toString("yyyy-MM-dd")), "yyyy-MM-dd"))
        valid_until = QDateEdit()
        valid_until.setCalendarPopup(True)
        valid_until.setDate(
            QDate.fromString(str(discount['valid_until'] or QDate.currentDate().addDays(30).toString("yyyy-MM-dd")),
                             "yyyy-MM-dd"))

        max_uses = QSpinBox()
        max_uses.setRange(0, 10000)
        max_uses.setValue(discount['max_uses'] or 0)
        max_uses.setSpecialValueText("Neomezeno")

        layout.addRow("Kód:", code_input)
        layout.addRow("Typ:", discount_type)
        layout.addRow("Hodnota:", value)
        layout.addRow("Aktivní:", active)
        layout.addRow("Od:", valid_from)
        layout.addRow("Do:", valid_until)
        layout.addRow("Max použití:", max_uses)

        btn = QPushButton("Uložit změny")
        btn.clicked.connect(lambda: self.save_discount(code_input.text(), discount_type.currentText(), value.value(),
                                                       active.isChecked(), valid_from.date().toString("yyyy-MM-dd"),
                                                       valid_until.date().toString("yyyy-MM-dd"), max_uses.value(),
                                                       dialog, is_edit=True, discount_id=discount_id))
        layout.addRow(btn)
        dialog.exec_()

    def save_discount(self, code, discount_type, value, active, valid_from, valid_until, max_uses, dialog,
                      is_edit=False, discount_id=None):
        if not code: return
        conn = get_db_connection()
        if not conn: return
        cursor = conn.cursor()
        try:
            if is_edit:
                cursor.execute(
                    "UPDATE discount_codes SET code=%s, discount_type=%s, discount_value=%s, is_active=%s, valid_from=%s, valid_until=%s, max_uses=%s WHERE id=%s",
                    (code.upper(), discount_type, value, 1 if active else 0, valid_from, valid_until,
                     max_uses if max_uses > 0 else None, discount_id))
            else:
                cursor.execute(
                    "INSERT INTO discount_codes (code, discount_type, discount_value, is_active, valid_from, valid_until, max_uses) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (code.upper(), discount_type, value, 1 if active else 0, valid_from, valid_until,
                     max_uses if max_uses > 0 else None))
            conn.commit()
            dialog.close()
            self.load_discounts()
        finally:
            cursor.close()
            conn.close()

    def delete_discount(self, discount_id):
        if QMessageBox.question(self, "Potvrzení", "Smazat?") == QMessageBox.Yes:
            conn = get_db_connection()
            if not conn: return
            cursor = conn.cursor()
            cursor.execute("DELETE FROM discount_codes WHERE id = %s", (discount_id,))
            conn.commit()
            cursor.close()
            conn.close()
            self.load_discounts()


# ─── ZÁLOŽKA: NOVINKY ───
class NewsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_news()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("Správa novinek")
        title.setStyleSheet("color: #e84118; font-size: 24px;")
        layout.addWidget(title)

        self.news_table = QTableWidget()
        self.news_table.setColumnCount(5)
        self.news_table.setHorizontalHeaderLabels(["ID", "Název", "Datum", "Aktivní", "Akce"])
        self.news_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.news_table.verticalHeader().setDefaultSectionSize(50)
        layout.addWidget(self.news_table)

        add_btn = QPushButton("Přidat novinku")
        add_btn.clicked.connect(self.show_add_news_dialog)
        layout.addWidget(add_btn, alignment=Qt.AlignLeft)

    def load_news(self):
        conn = get_db_connection()
        if not conn: return
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, date, is_active FROM news")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        self.news_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.news_table.setItem(row_idx, 0, QTableWidgetItem(str(row['id'])))
            self.news_table.setItem(row_idx, 1, QTableWidgetItem(row['title']))
            self.news_table.setItem(row_idx, 2, QTableWidgetItem(str(row['date'])))
            self.news_table.setItem(row_idx, 3, QTableWidgetItem("Ano" if row['is_active'] else "Ne"))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)

            edit_btn = QPushButton("Upravit")
            edit_btn.setStyleSheet("background-color: #7f8fa6;")
            edit_btn.clicked.connect(lambda _, rid=row['id']: self.show_edit_news_dialog(rid))

            delete_btn = QPushButton("Smazat")
            delete_btn.setStyleSheet("background-color: #ff3f34;")
            delete_btn.clicked.connect(lambda _, rid=row['id']: self.delete_news(rid))

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.news_table.setCellWidget(row_idx, 4, actions_widget)

    def show_add_news_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Přidat novinku")
        layout = QFormLayout(dialog)

        title = QLineEdit()
        content = QTextEdit()
        date = QDateEdit()
        date.setDate(QDate.currentDate())
        date.setCalendarPopup(True)
        active = QCheckBox("Zobrazovat")
        active.setChecked(True)

        layout.addRow("Název:", title)
        layout.addRow("Obsah:", content)
        layout.addRow("Datum:", date)
        layout.addRow("Aktivní:", active)

        btn = QPushButton("Uložit")
        btn.clicked.connect(
            lambda: self.save_news(title.text(), content.toPlainText(), date.date().toString("yyyy-MM-dd"),
                                   active.isChecked(), dialog))
        layout.addRow(btn)
        dialog.exec_()

    def show_edit_news_dialog(self, news_id):
        conn = get_db_connection()
        if not conn: return
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM news WHERE id = %s", (news_id,))
        news = cursor.fetchone()
        cursor.close()
        conn.close()

        if not news: return
        dialog = QDialog(self)
        layout = QFormLayout(dialog)

        title = QLineEdit(news['title'])
        content = QTextEdit(news['content'])
        date = QDateEdit()
        date.setDate(QDate.fromString(str(news['date']), "yyyy-MM-dd"))
        date.setCalendarPopup(True)
        active = QCheckBox("Zobrazovat")
        active.setChecked(news['is_active'])

        layout.addRow("Název:", title)
        layout.addRow("Obsah:", content)
        layout.addRow("Datum:", date)
        layout.addRow("Aktivní:", active)

        btn = QPushButton("Uložit změny")
        btn.clicked.connect(
            lambda: self.save_news(title.text(), content.toPlainText(), date.date().toString("yyyy-MM-dd"),
                                   active.isChecked(), dialog, is_edit=True, news_id=news_id))
        layout.addRow(btn)
        dialog.exec_()

    def save_news(self, title, content, date, active, dialog, is_edit=False, news_id=None):
        if not title or not content: return
        conn = get_db_connection()
        if not conn: return
        cursor = conn.cursor()
        try:
            if is_edit:
                cursor.execute("UPDATE news SET title=%s, content=%s, date=%s, is_active=%s WHERE id=%s",
                               (title, content, date, 1 if active else 0, news_id))
            else:
                cursor.execute("INSERT INTO news (title, content, date, is_active) VALUES (%s, %s, %s, %s)",
                               (title, content, date, 1 if active else 0))
            conn.commit()
            dialog.close()
            self.load_news()
        finally:
            cursor.close()
            conn.close()

    def delete_news(self, news_id):
        if QMessageBox.question(self, "Potvrzení", "Smazat?") == QMessageBox.Yes:
            conn = get_db_connection()
            if not conn: return
            cursor = conn.cursor()
            cursor.execute("DELETE FROM news WHERE id = %s", (news_id,))
            conn.commit()
            cursor.close()
            conn.close()
            self.load_news()


# ─── HLAVNÍ OKNO ───
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FLOSE Admin Panel")
        self.setGeometry(100, 100, 1300, 850)
        self.setStyleSheet(MAIN_STYLE)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tabs.addTab(ProductsTab(), "Produkty")
        self.tabs.addTab(DiscountsTab(), "Slevy")
        self.tabs.addTab(NewsTab(), "Novinky")

from flask import render_template, request, redirect, url_for, session, flash
from .database import get_db_connection
from decimal import Decimal
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import re

def is_valid_card_number(card_number):
    """Kontrola platnosti čísla karty pomocí Luhnova algoritmu"""

    card_number = card_number.replace(" ", "").replace("-", "")

    if not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
        return False

    # Luhn algoritmus
    digits = [int(d) for d in card_number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]

    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(divmod(d * 2, 10))

    return checksum % 10 == 0

def register_routes(app):
    @app.route('/')
    def index():
        conn = get_db_connection()
        if conn is None:
            flash('Chyba připojení k databázi', 'error')
            return render_template('index.html', products=[])

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('index.html', products=products)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            conn = get_db_connection()
            if conn is None:
                flash('Chyba databáze', 'error')
                return redirect(url_for('login'))

            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Přihlášení úspěšné!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Špatné jméno nebo heslo.', 'error')

        return render_template('login.html')

    def is_valid_password(password):
        """
        Kontrola hesla - vrací (True/False, chybová zpráva)
        """
        if len(password) < 8:
            return False, "Heslo musí mít alespoň 8 znaků"
        if not re.search(r'[A-Z]', password):
            return False, "Heslo musí obsahovat alespoň jedno velké písmeno (A-Z)"
        if not re.search(r'[a-z]', password):
            return False, "Heslo musí obsahovat alespoň jedno malé písmeno (a-z)"
        if not re.search(r'\d', password):
            return False, "Heslo musí obsahovat alespoň jednu číslici (0-9)"
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\"\',.<>?/\\|`~]', password):
            return False, "Heslo musí obsahovat alespoň jeden speciální znak (např. !@#$%^&*)"
        return True, ""

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')

            # 1. Kontrola, jestli všechna pole jsou vyplněná
            if not all([username, email, password]):
                flash('Vyplňte všechna pole.', 'error')
                return render_template('register.html')

            # 2. Kontrola hesla – zde se to vše hlídá
            valid, error_msg = is_valid_password(password)
            if not valid:
                flash(error_msg, 'error')
                return render_template('register.html')

            # 3. Hash hesla (nikdy neukládáme plain text!)
            hashed_password = generate_password_hash(password)

            conn = get_db_connection()
            if conn is None:
                flash('Chyba připojení k databázi.', 'error')
                return render_template('register.html')

            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_password)
                )
                conn.commit()
                flash('Registrace úspěšná! Nyní se můžete přihlásit.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                flash('Uživatelské jméno nebo email již existuje.', 'error')
            finally:
                cursor.close()
                conn.close()

        return render_template('register.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Odhlášení úspěšné.', 'success')
        return redirect(url_for('index'))

    # ─── KOŠÍK ROUTY ─── (přidej tyto 3 funkce sem na konec)

    @app.route('/cart/add', methods=['POST'])
    def add_to_cart():
        if 'user_id' not in session:
            flash('Pro přidání do košíku se přihlaste.', 'error')
            return redirect(url_for('login'))

        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity', 1) or 1)

        conn = get_db_connection()
        if conn is None:
            flash('Chyba připojení k databázi.', 'error')
            return redirect(url_for('index'))

        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO cart (user_id, product_id, quantity) 
                VALUES (%s, %s, %s) 
                ON DUPLICATE KEY UPDATE quantity = quantity + %s
                """,
                (session['user_id'], product_id, quantity, quantity)
            )
            conn.commit()
            flash('Produkt přidán do košíku!', 'success')
        except Exception as e:
            flash(f'Chyba při přidávání: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('produkty'))

    @app.route('/cart')
    def cart():
        if 'user_id' not in session:
            flash('Pro zobrazení košíku se přihlaste.', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        if conn is None:
            flash('Chyba připojení k databázi.', 'error')
            return redirect(url_for('index'))

        cursor = conn.cursor(dictionary=True)
        # ÚPRAVA: Přidáno p.discount_percent do SELECTu
        cursor.execute("""
            SELECT p.id, p.name, p.price, p.discount_percent, p.image_url, c.quantity
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cursor.fetchall()

        # ÚPRAVA: Přepočet ceny s ohledem na procentuální slevu produktu
        total = Decimal('0')
        for item in cart_items:
            base_price = Decimal(str(item['price']))
            discount_pct = Decimal(str(item.get('discount_percent') or 0))

            if discount_pct > Decimal('0'):
                discount_amount = (base_price * discount_pct / Decimal('100'))
                unit_price = base_price - discount_amount
            else:
                unit_price = base_price

            total += unit_price * Decimal(str(item['quantity']))

        # Sleva ze session (Slevový kód aplikovaný na celý košík)
        discount = Decimal(str(session.get('discount', 0)))
        total_after_discount = max(Decimal('0'), total - discount)

        cursor.close()
        conn.close()

        return render_template(
            'cart.html',
            cart_items=cart_items,
            total=float(total),
            discount=float(discount),
            total_after_discount=float(total_after_discount)
        )

    @app.route('/cart/apply_discount', methods=['POST'])
    def apply_discount():
        if 'user_id' not in session:
            flash('Pro použití slevy se přihlaste.', 'error')
            return redirect(url_for('login'))

        code = request.form.get('discount_code', '').strip().upper()

        conn = get_db_connection()
        if conn is None:
            flash('Chyba připojení k databázi.', 'error')
            return redirect(url_for('cart'))

        try:
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT discount_type, discount_value, is_active, valid_from, valid_until, max_uses, used_count
                FROM discount_codes
                WHERE code = %s
            """, (code,))
            discount_row = cursor.fetchone()

            if not discount_row:
                flash('Neplatný slevový kód.', 'error')
                return redirect(url_for('cart'))

            if not discount_row['is_active']:
                flash('Tento slevový kód již není aktivní.', 'error')
                return redirect(url_for('cart'))

            today = datetime.now().date()

            if discount_row['valid_from'] and discount_row['valid_from'] > today:
                flash('Slevový kód ještě není platný.', 'error')
                return redirect(url_for('cart'))

            if discount_row['valid_until'] and discount_row['valid_until'] < today:
                flash('Slevový kód již vypršel.', 'error')
                return redirect(url_for('cart'))

            if discount_row['max_uses'] is not None and discount_row['used_count'] >= discount_row['max_uses']:
                flash('Tento slevový kód již byl použit maximální početkrát.', 'error')
                return redirect(url_for('cart'))

            # ÚPRAVA: Přidáno p.discount_percent do SELECTu i tady,
            # aby se hodnota košíku spočítala správně ze zlevněných produktů
            cursor.execute("""
                SELECT p.price, p.discount_percent, c.quantity
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.user_id = %s
            """, (session['user_id'],))
            items = cursor.fetchall()

            # ÚPRAVA: Přepočet ceny košíku se zohledněním slev produktů
            total = Decimal('0')
            for item in items:
                base_price = Decimal(str(item['price']))
                discount_pct = Decimal(str(item.get('discount_percent') or 0))

                if discount_pct > Decimal('0'):
                    discount_amount = (base_price * discount_pct / Decimal('100'))
                    unit_price = base_price - discount_amount
                else:
                    unit_price = base_price

                total += unit_price * Decimal(str(item['quantity']))

            if total <= 0:
                flash('Košík má nulovou hodnotu.', 'error')
                return redirect(url_for('cart'))

            # Výpočet slevy ze slevového kódu
            if discount_row['discount_type'] == 'percent':
                discount = (total * Decimal(str(discount_row['discount_value'])) / Decimal('100')).quantize(
                    Decimal('0.01'))
            else:
                discount = Decimal(str(discount_row['discount_value'])).quantize(Decimal('0.01'))

            discount = min(discount, total)

            session['discount'] = float(discount)
            session['discount_code'] = code

            # Zvýšíme počet použití
            cursor.execute("""
                UPDATE discount_codes 
                SET used_count = used_count + 1 
                WHERE code = %s
            """, (code,))
            conn.commit()

            flash(f'Sleva "{code}" použita! Odečteno {discount} Kč.', 'success')

        except Exception as e:
            flash(f'Chyba při uplatnění slevy: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('cart'))

    @app.route('/cart/remove/<int:product_id>')
    def remove_from_cart(product_id):
        if 'user_id' not in session:
            flash('Pro odebrání z košíku se přihlaste.', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        if conn is None:
            flash('Chyba databáze', 'error')
            return redirect(url_for('cart'))

        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM cart WHERE user_id = %s AND product_id = %s",
            (session['user_id'], product_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash('Produkt odebrán z košíku.', 'success')
        return redirect(url_for('cart'))

    @app.route('/cart/update', methods=['POST'])
    def update_cart():
        if 'user_id' not in session:
            flash('Pro úpravu košíku se přihlaste.', 'error')
            return redirect(url_for('login'))

        product_id = request.form.get('product_id')
        try:
            # Převedeme na int, a pokud to nejde nebo je to prázdné, dáme 1
            quantity = int(request.form.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        # Pokud uživatel zadá 0 nebo méně, produkt prostě smažeme
        if quantity < 1:
            return redirect(url_for('remove_from_cart', product_id=product_id))

        conn = get_db_connection()
        if conn is None:
            flash('Chyba připojení k databázi.', 'error')
            return redirect(url_for('cart'))

        cursor = conn.cursor()
        try:
            # Aktualizace množství v databázi
            cursor.execute(
                "UPDATE cart SET quantity = %s WHERE user_id = %s AND product_id = %s",
                (quantity, session['user_id'], product_id)
            )
            conn.commit()

            # DŮLEŽITÉ: Pokud změníme množství, zrušíme aktuální slevu,
            # aby se musela přepočítat z nové celkové ceny.
            if 'discount' in session:
                session.pop('discount', None)
                session.pop('discount_code', None)
                flash('Množství upraveno. Slevu je nutné uplatnit znovu pro správný výpočet.', 'info')
            else:
                flash('Množství bylo úspěšně upraveno.', 'success')

        except Exception as e:
            flash(f'Chyba při úpravě množství: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('cart'))

    @app.route('/process_payment', methods=['POST'])
    def process_payment():
        if 'user_id' not in session:
            flash('Pro dokončení objednávky se přihlaste.', 'error')
            return redirect(url_for('login'))

        # === 1. NAČTENÍ ÚDAJŮ Z FORMULÁŘE ===
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        zip_code = request.form.get('zip_code', '').strip()

        card_number = request.form.get('card_number', '').strip()
        expiry = request.form.get('expiry', '').strip()
        cvc = request.form.get('cvc', '').strip()
        card_holder = request.form.get('card_holder', '').strip()

        session['payment_form_data'] = {
            'first_name': first_name,
            'last_name': last_name,
            'address': address,
            'city': city,
            'zip_code': zip_code,
            'card_number': card_number,
            'expiry': expiry,
            'card_holder': card_holder
        }

        return_url = url_for('cart', payment_error=1)

        # === KONTROLY (Okamžité ukončení při první chybě) ===
        if not first_name or not last_name or not address or not city or not zip_code:
            flash('Vyplňte prosím všechny doručovací údaje.', 'error')
            return redirect(return_url)

        if not card_number or not expiry or not cvc or not card_holder:
            flash('Vyplňte všechny platební údaje.', 'error')
            return redirect(return_url)

        name_pattern = r'^[A-Za-zÁČĎÉĚÍŇÓŘŠŤÚŮÝŽáčďéěíňóřšťúůýž\s\-]{2,}$'
        if not re.match(name_pattern, card_holder):
            flash('Jméno držitele karty může obsahovat pouze písmena, mezery a pomlčky.', 'error')
            return redirect(return_url)

        words = card_holder.strip().split()
        if len(words) < 2:
            flash('Jméno držitele karty musí obsahovat jméno a příjmení (alespoň dvě slova).', 'error')
            return redirect(return_url)

        if any(len(word) < 2 for word in words):
            flash('Každé slovo ve jméně musí mít alespoň 2 znaky (např. Jan Novák).', 'error')
            return redirect(return_url)

        if not re.match(r'^\d{2}/\d{2}$', expiry):
            flash('Platnost musí být ve formátu MM/RR.', 'error')
            return redirect(return_url)

        try:
            month, year = map(int, expiry.split('/'))
            if month < 1 or month > 12:
                raise ValueError

            current_date = datetime.now()
            input_year = year + 2000 if year < 100 else year

            if month == 12:
                expiry_date = datetime(input_year + 1, 1, 1) - timedelta(days=1)
            else:
                expiry_date = datetime(input_year, month + 1, 1) - timedelta(days=1)

            if expiry_date < current_date:
                flash('Karta již není platná (vypršela platnost).', 'error')
                return redirect(return_url)
        except (ValueError, TypeError):
            flash('Neplatný formát platnosti karty nebo neexistující měsíc.', 'error')
            return redirect(return_url)

        if not is_valid_card_number(card_number):
            flash('Neplatné číslo karty (Luhn kontrola selhala).', 'error')
            return redirect(return_url)

        if len(cvc) != 3 or not cvc.isdigit():
            flash('Neplatný CVC kód. Musí obsahovat přesně 3 číslice.', 'error')
            return redirect(return_url)

        # === VŠECHNO JE V POŘÁDKU → provedeme platbu ===
        conn = get_db_connection()
        if conn is None:
            flash('Chyba připojení k databázi.', 'error')
            return redirect(return_url)

        cursor = conn.cursor(dictionary=True)

        try:
            # ÚPRAVA 1: Načítáme k položkám i p.discount_percent
            cursor.execute("""
                SELECT c.product_id, c.quantity, p.price, p.discount_percent
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.user_id = %s
            """, (session['user_id'],))
            cart_items = cursor.fetchall()

            if not cart_items:
                flash('Košík je prázdný – objednávka nebyla vytvořena.', 'error')
                return redirect(return_url)

            # ÚPRAVA 2: Vypočítáme slevy a uložíme si OPRAVDOVOU cenu každého kusu
            total = Decimal('0')
            processed_items = []

            for item in cart_items:
                base_price = Decimal(str(item['price']))
                discount_pct = Decimal(str(item.get('discount_percent') or 0))

                if discount_pct > Decimal('0'):
                    discount_amount = (base_price * discount_pct / Decimal('100'))
                    unit_price = base_price - discount_amount
                else:
                    unit_price = base_price

                total += unit_price * Decimal(str(item['quantity']))

                # Tady si tu správnou akční cenu schováme pro pozdější zápis do databáze
                processed_items.append({
                    'product_id': item['product_id'],
                    'quantity': item['quantity'],
                    'final_price': unit_price
                })

            discount_coupon = Decimal(str(session.get('discount', 0)))
            total_after_discount = max(Decimal('0'), total - discount_coupon)

            # Uložíme celou objednávku
            cursor.execute("""
                INSERT INTO orders (user_id, total_price, status, first_name, last_name, address, city, zip_code)
                VALUES (%s, %s, 'completed', %s, %s, %s, %s, %s)
            """, (session['user_id'], total_after_discount, first_name, last_name, address, city, zip_code))
            order_id = cursor.lastrowid

            # ÚPRAVA 3: Zapisujeme item['final_price'] namísto původní ceny
            for item in processed_items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, price_at_time)
                    VALUES (%s, %s, %s, %s)
                """, (order_id, item['product_id'], item['quantity'], item['final_price']))

            cursor.execute("DELETE FROM cart WHERE user_id = %s", (session['user_id'],))
            conn.commit()

            # VYMAZÁNÍ DOČASNÝCH DAT
            session.pop('payment_form_data', None)
            session.pop('discount', None)
            session.pop('discount_code', None)

            flash('Platba úspěšně provedena! Objednávka byla uložena. Děkujeme!', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Chyba při zpracování objednávky: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('index'))


    @app.route('/novinky')
    def novinky():
        conn = get_db_connection()
        if conn is None:
            flash('Chyba připojení k databázi', 'error')
            news = []
        else:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT title, content, date 
                FROM news 
                WHERE is_active = 1 
                ORDER BY date DESC
            """)
            news = cursor.fetchall()
            cursor.close()
            conn.close()

        return render_template('novinky.html', news=news)
    @app.route('/produkty')
    def produkty():
        conn = get_db_connection()
        if conn is None:
            flash('Chyba databáze', 'error')
            return render_template('produkty.html', products=[])

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template('produkty.html', products=products)


    @app.route('/search')
    def search():
        query = request.args.get('q', '').strip()

        if not query:
            return render_template('search.html', products=[], query='')

        conn = get_db_connection()
        if conn is None:
            flash('Chyba databáze', 'error')
            return render_template('search.html', products=[], query=query)

        cursor = conn.cursor(dictionary=True)
        # Vyhledávání podle názvu (LIKE pro částečnou shodu)
        cursor.execute(
            "SELECT * FROM products WHERE name LIKE %s ORDER BY name",
            (f"%{query}%",)
        )
        products = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template('search.html', products=products, query=query)

    def clean_product_name(name):
        """Odstraní pomlčky, lomítka, duplicitní slova (např. zdvojené značky) a vyhladí mezery."""
        if not name:
            return name
        # Odstranění pomlček a lomítek
        name = re.sub(r'[-/]', ' ', name)
        # Odstranění duplicitních po sobě jdoucích slov
        name = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', name, flags=re.IGNORECASE)
        # Vyčištění vícenásobných mezer
        return ' '.join(name.split())

    @app.route('/profile')
    def profile():
        if 'user_id' not in session:
            flash('Pro zobrazení historie se přihlaste.', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        if conn is None:
            flash('Chyba databáze', 'error')
            return redirect(url_for('index'))

        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
                SELECT id, order_date, total_price
                FROM orders
                WHERE user_id = %s
                ORDER BY order_date DESC
            """, (session['user_id'],))
        orders = cursor.fetchall()

        for order in orders:
            cursor.execute("""
                    SELECT p.name, oi.quantity, oi.price_at_time
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = %s
                """, (order['id'],))

            fetched_items = cursor.fetchall()

            # Aplikování čistého textu na názvy produktů v objednávce (odstranění pomlček, duplicitních značek atd.)
            for item in fetched_items:
                item['name'] = clean_product_name(item['name'])

            # OPRAVA: Přejmenováno z 'items' na 'order_products'
            order['order_products'] = fetched_items

        cursor.close()
        conn.close()

        return render_template('profile.html', orders=orders, active_tab='orders')

    @app.route('/profile/reviews')
    def my_reviews():
        if 'user_id' not in session:
            flash('Pro zobrazení recenzí se přihlaste.', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        # Přidána i sem kontrola spojení pro prevenci pádu
        if conn is None:
            flash('Chyba databáze', 'error')
            return redirect(url_for('index'))

        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
                SELECT r.id, r.rating, r.comment, r.created_at, p.name as product_name, p.image_url
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                WHERE r.user_id = %s
                ORDER BY r.created_at DESC
            """, (session['user_id'],))

        reviews = cursor.fetchall()

        # Aplikování čistého textu na názvy produktů u recenzí
        for review in reviews:
            review['product_name'] = clean_product_name(review['product_name'])

        cursor.close()
        conn.close()

        return render_template('profile.html', reviews=reviews, active_tab='reviews')

    @app.route('/product/<int:product_id>')
    def product_detail(product_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()

        if not product:
            flash('Produkt nebyl nalezen.', 'error')
            return redirect(url_for('index'))

        # Načtení recenzí
        cursor.execute("""
            SELECT r.*, u.username 
            FROM reviews r 
            JOIN users u ON r.user_id = u.id 
            WHERE r.product_id = %s 
            ORDER BY r.created_at DESC
        """, (product_id,))
        reviews = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('product_detail.html',
                               product=product,
                               reviews=reviews)
    @app.route('/product/<int:product_id>/review', methods=['POST'])
    def add_review(product_id):
        if 'user_id' not in session:
            flash('Pro přidání recenze se musíš přihlásit.', 'error')
            return redirect(url_for('login'))

        rating = int(request.form.get('rating'))
        comment = request.form.get('comment', '').strip()

        if not (1 <= rating <= 5):
            flash('Hodnocení musí být mezi 1 a 5 hvězdičkami.', 'error')
            return redirect(url_for('product_detail', product_id=product_id))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO reviews (product_id, user_id, rating, comment)
                VALUES (%s, %s, %s, %s)
            """, (product_id, session['user_id'], rating, comment))
            conn.commit()
            flash('Recenze byla úspěšně přidána!', 'success')
        except Exception as e:
            flash('Chyba při přidávání recenze.', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('product_detail', product_id=product_id))

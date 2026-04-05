import unittest
import re
# Místo hotové aplikace importujeme tvoji tovární funkci
from app import create_app


class TestFloseEshop(unittest.TestCase):

    def setUp(self):
        # 1. Vyrobíme si čistou testovací aplikaci
        self.app = create_app()
        self.app.config['TESTING'] = True

        # 2. Vytvoříme si virtuálního robota (prohlížeč) pro klikání
        self.client = self.app.test_client()

    # --- TEST 1: Kontrola hlavní stránky (Web Routing) ---
    def test_01_homepage_loads(self):
        # Virtuální prohlížeč zkusí načíst úvodní stránku
        response = self.client.get('/')

        # Očekáváme HTTP kód 200 (Vše je OK)
        self.assertEqual(response.status_code, 200, "Úvodní stránka se nenačetla správně!")

    # --- TEST 2: Kontrola zabezpečení košíku (Security/Auth) ---
    def test_02_cart_requires_login(self):
        # Virtuální prohlížeč (který NENÍ přihlášený) zkusí jít do košíku
        response = self.client.get('/cart')

        # Očekáváme HTTP kód 302 (Přesměrování na login), protože tam nemá co dělat
        self.assertEqual(response.status_code, 302, "Chyba zabezpečení: Nepřihlášený uživatel se dostal do košíku!")

    # --- TEST 3: Kontrola logiky čištění názvů (Pure Python Logic) ---
    def test_03_text_cleaning_logic(self):
        # Tento test vůbec nepotřebuje web ani databázi, testuje jen naši logiku
        raw_name = "Nike - Mercurial / Vapor 16 Nike"

        # Naše čistící logika z administrace
        clean_name = re.sub(r'[-/]', ' ', raw_name)
        words = clean_name.split()
        unique_words = []
        seen = set()
        for w in words:
            if w.lower() not in seen:
                seen.add(w.lower())
                unique_words.append(w)
        final_name = " ".join(unique_words).strip()

        # Očekávaný výsledek: bez pomlček, lomítek a smazané duplicitní slovo "Nike"
        expected_name = "Nike Mercurial Vapor 16"

        # Ověření, jestli logika funguje
        self.assertEqual(final_name, expected_name, "Čištění textu nefunguje správně!")


if __name__ == '__main__':
    unittest.main()

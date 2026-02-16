# -*- coding: utf-8 -*-
"""
Gelişmiş Nesne Yönelimli (OOP) Hesap Makinesi
Temel ve bilimsel işlemler, geçmiş kayıtları, hata yönetimi.
"""

import math
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  SOYUT İŞLEM SINIFI
# ═══════════════════════════════════════════════════════════════════

class Operation(ABC):
    """Tüm matematiksel işlemler için soyut temel sınıf."""

    @abstractmethod
    def execute(self, *args: float) -> float:
        """İşlemi gerçekleştir."""
        pass

    @abstractmethod
    def symbol(self) -> str:
        """İşlem sembolü."""
        pass


# ═══════════════════════════════════════════════════════════════════
#  TEMEL ARİTMETİK İŞLEMLER
# ═══════════════════════════════════════════════════════════════════

class Addition(Operation):
    def execute(self, a: float, b: float) -> float:
        return a + b

    def symbol(self) -> str:
        return "+"


class Subtraction(Operation):
    def execute(self, a: float, b: float) -> float:
        return a - b

    def symbol(self) -> str:
        return "-"


class Multiplication(Operation):
    def execute(self, a: float, b: float) -> float:
        return a * b

    def symbol(self) -> str:
        return "×"


class Division(Operation):
    def execute(self, a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Sıfıra bölme hatası!")
        return a / b

    def symbol(self) -> str:
        return "÷"


class Modulus(Operation):
    def execute(self, a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Sıfıra mod alma hatası!")
        return a % b

    def symbol(self) -> str:
        return "%"


class Power(Operation):
    def execute(self, a: float, b: float) -> float:
        return a ** b

    def symbol(self) -> str:
        return "^"


# ═══════════════════════════════════════════════════════════════════
#  BİLİMSEL İŞLEMLER (Tek Operand)
# ═══════════════════════════════════════════════════════════════════

class SquareRoot(Operation):
    def execute(self, a: float) -> float:
        if a < 0:
            raise ValueError("Negatif sayının karekökü alınamaz!")
        return math.sqrt(a)

    def symbol(self) -> str:
        return "√"


class Logarithm(Operation):
    def execute(self, a: float) -> float:
        if a <= 0:
            raise ValueError("0 veya negatif sayının logaritması alınamaz!")
        return math.log10(a)

    def symbol(self) -> str:
        return "log₁₀"


class NaturalLog(Operation):
    def execute(self, a: float) -> float:
        if a <= 0:
            raise ValueError("0 veya negatif sayının doğal logaritması alınamaz!")
        return math.log(a)

    def symbol(self) -> str:
        return "ln"


class Sine(Operation):
    def execute(self, a: float) -> float:
        return math.sin(math.radians(a))

    def symbol(self) -> str:
        return "sin"


class Cosine(Operation):
    def execute(self, a: float) -> float:
        return math.cos(math.radians(a))

    def symbol(self) -> str:
        return "cos"


class Tangent(Operation):
    def execute(self, a: float) -> float:
        return math.tan(math.radians(a))

    def symbol(self) -> str:
        return "tan"


class Factorial(Operation):
    def execute(self, a: float) -> float:
        if a < 0 or a != int(a):
            raise ValueError("Faktöriyel yalnızca pozitif tam sayılar için tanımlıdır!")
        return float(math.factorial(int(a)))

    def symbol(self) -> str:
        return "!"


# ═══════════════════════════════════════════════════════════════════
#  İŞLEM GEÇMİŞİ
# ═══════════════════════════════════════════════════════════════════

class HistoryRecord:
    """Tek bir işlem kaydı."""

    def __init__(self, expression: str, result: float):
        self.expression = expression
        self.result = result
        self.timestamp = datetime.now()

    def __str__(self) -> str:
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.expression} = {self.result}"


class HistoryManager:
    """İşlem geçmişini yönetir."""

    def __init__(self, max_records: int = 100):
        self._records: List[HistoryRecord] = []
        self._max_records = max_records

    def add(self, expression: str, result: float) -> None:
        record = HistoryRecord(expression, result)
        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records.pop(0)
        logger.debug("Geçmişe eklendi: %s", record)

    def get_all(self) -> List[HistoryRecord]:
        return list(self._records)

    def get_last(self, n: int = 5) -> List[HistoryRecord]:
        return self._records[-n:]

    def clear(self) -> None:
        self._records.clear()
        logger.info("Geçmiş temizlendi.")

    @property
    def count(self) -> int:
        return len(self._records)


# ═══════════════════════════════════════════════════════════════════
#  BELLEK YÖNETİCİSİ
# ═══════════════════════════════════════════════════════════════════

class MemoryManager:
    """Hesap makinesi bellek işlemleri (M+, M-, MR, MC)."""

    def __init__(self):
        self._value: float = 0.0

    def add(self, value: float) -> None:
        self._value += value

    def subtract(self, value: float) -> None:
        self._value -= value

    def recall(self) -> float:
        return self._value

    def clear(self) -> None:
        self._value = 0.0


# ═══════════════════════════════════════════════════════════════════
#  ANA HESAP MAKİNESİ
# ═══════════════════════════════════════════════════════════════════

class Calculator:
    """
    Gelişmiş OOP Hesap Makinesi.

    Özellikler:
        - Temel aritmetik: +, -, ×, ÷, %, ^
        - Bilimsel: √, log, ln, sin, cos, tan, !
        - İşlem geçmişi (max 100 kayıt)
        - Bellek işlemleri (M+, M-, MR, MC)
        - Kapsamlı hata yönetimi
    """

    OPERATIONS = {
        "+": Addition(),
        "-": Subtraction(),
        "*": Multiplication(),
        "/": Division(),
        "%": Modulus(),
        "^": Power(),
        "sqrt": SquareRoot(),
        "log": Logarithm(),
        "ln": NaturalLog(),
        "sin": Sine(),
        "cos": Cosine(),
        "tan": Tangent(),
        "!": Factorial(),
    }

    SCIENTIFIC_OPS = {"sqrt", "log", "ln", "sin", "cos", "tan", "!"}

    def __init__(self):
        self.history = HistoryManager()
        self.memory = MemoryManager()
        self._last_result: Optional[float] = None
        logger.info("Hesap Makinesi başlatıldı.")

    def calculate(self, op_key: str, a: float, b: float = 0.0) -> float:
        """
        İşlem gerçekleştir.

        Args:
            op_key: İşlem anahtarı (+, -, *, /, sqrt, sin, vb.)
            a: Birinci operand
            b: İkinci operand (bilimsel işlemlerde kullanılmaz)

        Returns:
            İşlem sonucu

        Raises:
            ValueError: Geçersiz işlem veya parametre
            ZeroDivisionError: Sıfıra bölme
        """
        operation = self.OPERATIONS.get(op_key)
        if operation is None:
            raise ValueError(f"Bilinmeyen işlem: '{op_key}'")

        if op_key in self.SCIENTIFIC_OPS:
            result = operation.execute(a)
            expression = f"{operation.symbol()}({a})"
        else:
            result = operation.execute(a, b)
            expression = f"{a} {operation.symbol()} {b}"

        # Sonucu yuvarla
        result = round(result, 10)
        self._last_result = result

        # Geçmişe ekle
        self.history.add(expression, result)

        return result

    @property
    def last_result(self) -> Optional[float]:
        return self._last_result

    def show_operations(self) -> None:
        """Mevcut işlemleri listele."""
        print("\n📋 Kullanılabilir İşlemler:")
        print("─" * 40)
        print("  Temel:    +  -  *  /  %  ^")
        print("  Bilimsel: sqrt  log  ln  sin  cos  tan  !")
        print("  Bellek:   M+  M-  MR  MC")
        print("  Diğer:    history  clear  quit")
        print("─" * 40)


# ═══════════════════════════════════════════════════════════════════
#  KONSOl ARAYÜZÜ
# ═══════════════════════════════════════════════════════════════════

class ConsoleUI:
    """Hesap makinesi konsol arayüzü."""

    def __init__(self):
        self.calc = Calculator()

    def run(self) -> None:
        """Ana döngü."""
        self._print_header()
        self.calc.show_operations()

        while True:
            try:
                user_input = input("\n🔢 İşlem: ").strip().lower()

                if user_input in ("quit", "exit", "q"):
                    print("\n👋 Hesap makinesi kapatıldı. Toplam işlem: "
                          f"{self.calc.history.count}")
                    break

                if user_input == "history":
                    self._show_history()
                    continue

                if user_input == "clear":
                    self.calc.history.clear()
                    print("🗑️ Geçmiş temizlendi.")
                    continue

                if user_input == "help":
                    self.calc.show_operations()
                    continue

                if user_input.startswith("m"):
                    self._handle_memory(user_input)
                    continue

                self._process_calculation(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 Çıkış yapıldı.")
                break
            except Exception as e:
                print(f"❌ Hata: {e}")

    def _process_calculation(self, user_input: str) -> None:
        """Kullanıcı girdisini işle ve hesapla."""
        parts = user_input.split()

        if len(parts) == 2:
            # Bilimsel işlem: sin 45, sqrt 16, vb.
            op_key, val = parts
            try:
                a = float(val)
            except ValueError:
                print("❌ Geçersiz sayı!")
                return
            result = self.calc.calculate(op_key, a)
            print(f"  ✅ {self.calc.OPERATIONS[op_key].symbol()}({a}) = {result}")

        elif len(parts) == 3:
            # Temel işlem: 5 + 3
            try:
                a = float(parts[0])
                op_key = parts[1]
                b = float(parts[2])
            except (ValueError, IndexError):
                print("❌ Format: <sayı> <işlem> <sayı>  veya  <işlem> <sayı>")
                return
            result = self.calc.calculate(op_key, a, b)
            print(f"  ✅ {a} {self.calc.OPERATIONS[op_key].symbol()} {b} = {result}")

        else:
            print("❌ Format: <sayı> <işlem> <sayı>  veya  <işlem> <sayı>")
            print("   Örnek: 5 + 3  |  sqrt 16  |  sin 45")

    def _handle_memory(self, cmd: str) -> None:
        """Bellek komutlarını işle."""
        if cmd == "mr":
            val = self.calc.memory.recall()
            print(f"  🔢 Bellek: {val}")
        elif cmd == "mc":
            self.calc.memory.clear()
            print("  🗑️ Bellek temizlendi.")
        elif cmd == "m+" and self.calc.last_result is not None:
            self.calc.memory.add(self.calc.last_result)
            print(f"  ➕ Belleğe eklendi: {self.calc.last_result}")
        elif cmd == "m-" and self.calc.last_result is not None:
            self.calc.memory.subtract(self.calc.last_result)
            print(f"  ➖ Bellekten çıkarıldı: {self.calc.last_result}")
        else:
            print("  ❌ Bellek komutu: M+ M- MR MC")

    def _show_history(self) -> None:
        """İşlem geçmişini göster."""
        records = self.calc.history.get_all()
        if not records:
            print("  📋 Geçmiş boş.")
            return
        print(f"\n📋 İşlem Geçmişi ({len(records)} kayıt):")
        print("─" * 50)
        for record in records:
            print(f"  {record}")

    @staticmethod
    def _print_header() -> None:
        print("╔" + "═" * 48 + "╗")
        print("║     🧮 Gelişmiş OOP Hesap Makinesi v2.0      ║")
        print("║     Temel + Bilimsel + Bellek İşlemleri       ║")
        print("╚" + "═" * 48 + "╝")


# ═══════════════════════════════════════════════════════════════════
#  ANA GİRİŞ NOKTASI
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ui = ConsoleUI()
    ui.run()

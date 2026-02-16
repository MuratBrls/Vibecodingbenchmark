# -*- coding: utf-8 -*-
"""
Advanced Calculator — OOP Architecture
Modüler, hata toleranslı, genişletilebilir hesap makinesi.
"""

import math
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

# ─── LOGGING YAPILANDIRMASI ──────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  SOYUT TEMEL SINIF
# ═══════════════════════════════════════════════════════════════════

class Operation(ABC):
    """Tüm işlemler için soyut temel sınıf."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def symbol(self) -> str:
        ...

    @abstractmethod
    def execute(self, a: float, b: float = 0) -> float:
        ...


# ═══════════════════════════════════════════════════════════════════
#  SOMUT İŞLEM SINIFLARI
# ═══════════════════════════════════════════════════════════════════

class Addition(Operation):
    name = "Toplama"
    symbol = "+"

    def execute(self, a: float, b: float = 0) -> float:
        return a + b


class Subtraction(Operation):
    name = "Çıkarma"
    symbol = "-"

    def execute(self, a: float, b: float = 0) -> float:
        return a - b


class Multiplication(Operation):
    name = "Çarpma"
    symbol = "×"

    def execute(self, a: float, b: float = 0) -> float:
        return a * b


class Division(Operation):
    name = "Bölme"
    symbol = "÷"

    def execute(self, a: float, b: float = 0) -> float:
        if b == 0:
            raise ZeroDivisionError("Sıfıra bölme tanımsızdır!")
        return a / b


class Power(Operation):
    name = "Üs Alma"
    symbol = "^"

    def execute(self, a: float, b: float = 0) -> float:
        try:
            return a ** b
        except OverflowError:
            raise OverflowError(f"{a}^{b} çok büyük bir sonuç üretiyor!")


class SquareRoot(Operation):
    name = "Karekök"
    symbol = "√"

    def execute(self, a: float, b: float = 0) -> float:
        if a < 0:
            raise ValueError("Negatif sayının karekökü alınamaz!")
        return math.sqrt(a)


class Modulus(Operation):
    name = "Mod Alma"
    symbol = "%"

    def execute(self, a: float, b: float = 0) -> float:
        if b == 0:
            raise ZeroDivisionError("Sıfıra mod alma tanımsızdır!")
        return a % b


# ═══════════════════════════════════════════════════════════════════
#  İŞLEM GEÇMİŞİ
# ═══════════════════════════════════════════════════════════════════

class HistoryEntry:
    """Tek bir işlem kaydı."""

    __slots__ = ("operation", "a", "b", "result")

    def __init__(self, operation: str, a: float, b: float, result: float):
        self.operation = operation
        self.a = a
        self.b = b
        self.result = result

    def __repr__(self) -> str:
        return f"{self.operation}: {self.a}, {self.b} = {self.result}"


class History:
    """İşlem geçmişi yöneticisi."""

    def __init__(self, max_size: int = 50):
        self._entries: List[HistoryEntry] = []
        self._max_size = max_size

    def add(self, operation: str, a: float, b: float, result: float):
        entry = HistoryEntry(operation, a, b, result)
        self._entries.append(entry)
        if len(self._entries) > self._max_size:
            self._entries.pop(0)
        logger.debug("Geçmişe eklendi: %s", entry)

    def get_all(self) -> List[HistoryEntry]:
        return self._entries.copy()

    def clear(self):
        self._entries.clear()
        logger.info("Geçmiş temizlendi.")

    @property
    def count(self) -> int:
        return len(self._entries)

    @property
    def last(self) -> Optional[HistoryEntry]:
        return self._entries[-1] if self._entries else None


# ═══════════════════════════════════════════════════════════════════
#  ANA HESAP MAKİNESİ SINIFI
# ═══════════════════════════════════════════════════════════════════

class Calculator:
    """
    Genişletilebilir hesap makinesi.
    Yeni işlemler register_operation() ile eklenir.
    """

    def __init__(self):
        self._operations: Dict[str, Operation] = {}
        self._history = History()
        self._register_defaults()

    def _register_defaults(self):
        """Varsayılan işlemleri kaydeder."""
        defaults = [
            Addition(), Subtraction(), Multiplication(),
            Division(), Power(), SquareRoot(), Modulus(),
        ]
        for op in defaults:
            self._operations[op.name] = op

    def register_operation(self, operation: Operation):
        """Yeni bir işlem türü kaydeder."""
        self._operations[operation.name] = operation
        logger.info("Yeni işlem kaydedildi: %s", operation.name)

    def calculate(self, op_name: str, a: float, b: float = 0) -> float:
        """İşlemi çalıştırır, geçmişe kaydeder."""
        if op_name not in self._operations:
            raise KeyError(f"Bilinmeyen işlem: {op_name}")

        op = self._operations[op_name]
        try:
            result = op.execute(a, b)
            self._history.add(op_name, a, b, result)
            return result
        except (ZeroDivisionError, ValueError, OverflowError):
            raise
        except Exception as e:
            logger.error("İşlem hatası (%s): %s", op_name, e)
            raise

    @property
    def operations(self) -> Dict[str, Operation]:
        return self._operations.copy()

    @property
    def history(self) -> History:
        return self._history


# ═══════════════════════════════════════════════════════════════════
#  KULLANICİ ARAYÜZÜ
# ═══════════════════════════════════════════════════════════════════

class CalculatorUI:
    """Terminal tabanlı kullanıcı arayüzü."""

    SINGLE_OPERAND_OPS = {"Karekök"}

    def __init__(self):
        self.calc = Calculator()

    def _print_header(self):
        print("=" * 45)
        print("  🧮 GELİŞMİŞ HESAP MAKİNESİ (OOP Edition)")
        print("  📐 Mimari: Abstract Factory + Strategy")
        print("=" * 45)

    def _print_menu(self):
        print("\n📋 İşlemler:")
        ops = list(self.calc.operations.items())
        for i, (name, op) in enumerate(ops, 1):
            print(f"  {i}. {op.symbol}  {name}")
        print(f"  {len(ops) + 1}. 📋 Geçmiş Göster")
        print(f"  {len(ops) + 2}. 🗑️  Geçmiş Temizle")
        print("  0. 🚪 Çıkış")

    def _get_float(self, prompt: str) -> float:
        while True:
            try:
                return float(input(prompt))
            except ValueError:
                print("❌ Geçersiz sayı! Tekrar deneyin.")

    def _show_history(self):
        entries = self.calc.history.get_all()
        if not entries:
            print("\n📋 Geçmiş boş.")
            return
        print(f"\n📋 İşlem Geçmişi ({self.calc.history.count} kayıt):")
        print("-" * 40)
        for i, entry in enumerate(entries, 1):
            print(f"  {i:>3}. {entry}")
        print("-" * 40)

    def run(self):
        """Ana döngü."""
        self._print_header()

        ops_list = list(self.calc.operations.keys())
        total_options = len(ops_list)

        while True:
            self._print_menu()
            choice = input("\n>> ").strip()

            if choice == "0":
                print("\n👋 Güle güle!")
                break

            try:
                idx = int(choice)
            except ValueError:
                print("❌ Geçersiz seçim!")
                continue

            # Geçmiş göster
            if idx == total_options + 1:
                self._show_history()
                continue

            # Geçmiş temizle
            if idx == total_options + 2:
                self.calc.history.clear()
                continue

            if idx < 1 or idx > total_options:
                print("❌ Geçersiz seçim!")
                continue

            op_name = ops_list[idx - 1]

            try:
                if op_name in self.SINGLE_OPERAND_OPS:
                    a = self._get_float("Sayı: ")
                    result = self.calc.calculate(op_name, a)
                    op = self.calc.operations[op_name]
                    print(f"\n✅ {op.symbol}{a} = {result}")
                else:
                    a = self._get_float("1. sayı: ")
                    b = self._get_float("2. sayı: ")
                    result = self.calc.calculate(op_name, a, b)
                    op = self.calc.operations[op_name]
                    print(f"\n✅ {a} {op.symbol} {b} = {result}")

            except ZeroDivisionError as e:
                print(f"❌ Bölme Hatası: {e}")
            except ValueError as e:
                print(f"❌ Değer Hatası: {e}")
            except OverflowError as e:
                print(f"❌ Taşma Hatası: {e}")
            except KeyError as e:
                print(f"❌ İşlem Hatası: {e}")
            except Exception as e:
                logger.exception("Beklenmeyen hata")
                print(f"❌ Beklenmeyen hata: {e}")


# ═══════════════════════════════════════════════════════════════════
#  GİRİŞ NOKTASI
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        ui = CalculatorUI()
        ui.run()
    except KeyboardInterrupt:
        print("\n\n👋 Program sonlandırıldı.")
    except Exception as e:
        logger.exception("Kritik hata")
        print(f"⛔ Kritik hata: {e}")

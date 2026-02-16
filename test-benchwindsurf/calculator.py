import math
from typing import Union, List
from dataclasses import dataclass
from enum import Enum

class Operation(Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    POWER = "power"
    SQRT = "sqrt"

@dataclass
class CalculationResult:
    operation: str
    operand1: Union[float, int]
    operand2: Union[float, int, None]
    result: Union[float, str]
    success: bool
    error: str = None

class Calculator:
    def __init__(self):
        self.history: List[CalculationResult] = []
        self.precision = 2
    
    def set_precision(self, precision: int) -> None:
        """Set decimal precision for results"""
        if precision >= 0:
            self.precision = precision
    
    def _round_result(self, result: float) -> float:
        """Round result to specified precision"""
        return round(result, self.precision)
    
    def add(self, a: Union[float, int], b: Union[float, int]) -> CalculationResult:
        try:
            result = self._round_result(a + b)
            calc_result = CalculationResult(
                operation=f"{a} + {b}",
                operand1=a,
                operand2=b,
                result=result,
                success=True
            )
            self.history.append(calc_result)
            return calc_result
        except Exception as e:
            error_result = CalculationResult(
                operation=f"{a} + {b}",
                operand1=a,
                operand2=b,
                result=f"Error: {str(e)}",
                success=False,
                error=str(e)
            )
            self.history.append(error_result)
            return error_result
    
    def subtract(self, a: Union[float, int], b: Union[float, int]) -> CalculationResult:
        try:
            result = self._round_result(a - b)
            calc_result = CalculationResult(
                operation=f"{a} - {b}",
                operand1=a,
                operand2=b,
                result=result,
                success=True
            )
            self.history.append(calc_result)
            return calc_result
        except Exception as e:
            error_result = CalculationResult(
                operation=f"{a} - {b}",
                operand1=a,
                operand2=b,
                result=f"Error: {str(e)}",
                success=False,
                error=str(e)
            )
            self.history.append(error_result)
            return error_result
    
    def multiply(self, a: Union[float, int], b: Union[float, int]) -> CalculationResult:
        try:
            result = self._round_result(a * b)
            calc_result = CalculationResult(
                operation=f"{a} × {b}",
                operand1=a,
                operand2=b,
                result=result,
                success=True
            )
            self.history.append(calc_result)
            return calc_result
        except Exception as e:
            error_result = CalculationResult(
                operation=f"{a} × {b}",
                operand1=a,
                operand2=b,
                result=f"Error: {str(e)}",
                success=False,
                error=str(e)
            )
            self.history.append(error_result)
            return error_result
    
    def divide(self, a: Union[float, int], b: Union[float, int]) -> CalculationResult:
        try:
            if b == 0:
                raise ZeroDivisionError("Division by zero is not allowed")
            result = self._round_result(a / b)
            calc_result = CalculationResult(
                operation=f"{a} ÷ {b}",
                operand1=a,
                operand2=b,
                result=result,
                success=True
            )
            self.history.append(calc_result)
            return calc_result
        except ZeroDivisionError as e:
            error_result = CalculationResult(
                operation=f"{a} ÷ {b}",
                operand1=a,
                operand2=b,
                result=f"Error: {str(e)}",
                success=False,
                error=str(e)
            )
            self.history.append(error_result)
            return error_result
        except Exception as e:
            error_result = CalculationResult(
                operation=f"{a} ÷ {b}",
                operand1=a,
                operand2=b,
                result=f"Error: {str(e)}",
                success=False,
                error=str(e)
            )
            self.history.append(error_result)
            return error_result
    
    def power(self, a: Union[float, int], b: Union[float, int]) -> CalculationResult:
        try:
            result = self._round_result(a ** b)
            calc_result = CalculationResult(
                operation=f"{a}^{b}",
                operand1=a,
                operand2=b,
                result=result,
                success=True
            )
            self.history.append(calc_result)
            return calc_result
        except Exception as e:
            error_result = CalculationResult(
                operation=f"{a}^{b}",
                operand1=a,
                operand2=b,
                result=f"Error: {str(e)}",
                success=False,
                error=str(e)
            )
            self.history.append(error_result)
            return error_result
    
    def sqrt(self, a: Union[float, int]) -> CalculationResult:
        try:
            if a < 0:
                raise ValueError("Cannot calculate square root of negative number")
            result = self._round_result(math.sqrt(a))
            calc_result = CalculationResult(
                operation=f"√{a}",
                operand1=a,
                operand2=None,
                result=result,
                success=True
            )
            self.history.append(calc_result)
            return calc_result
        except ValueError as e:
            error_result = CalculationResult(
                operation=f"√{a}",
                operand1=a,
                operand2=None,
                result=f"Error: {str(e)}",
                success=False,
                error=str(e)
            )
            self.history.append(error_result)
            return error_result
        except Exception as e:
            error_result = CalculationResult(
                operation=f"√{a}",
                operand1=a,
                operand2=None,
                result=f"Error: {str(e)}",
                success=False,
                error=str(e)
            )
            self.history.append(error_result)
            return error_result
    
    def get_history(self) -> List[CalculationResult]:
        return self.history.copy()
    
    def clear_history(self) -> None:
        self.history.clear()
    
    def get_successful_operations(self) -> List[CalculationResult]:
        return [calc for calc in self.history if calc.success]
    
    def get_failed_operations(self) -> List[CalculationResult]:
        return [calc for calc in self.history if not calc.success]
    
    def calculate(self, operation: Operation, a: Union[float, int], b: Union[float, int] = None) -> CalculationResult:
        """Generic calculation method"""
        if operation == Operation.ADD:
            return self.add(a, b)
        elif operation == Operation.SUBTRACT:
            return self.subtract(a, b)
        elif operation == Operation.MULTIPLY:
            return self.multiply(a, b)
        elif operation == Operation.DIVIDE:
            return self.divide(a, b)
        elif operation == Operation.POWER:
            return self.power(a, b)
        elif operation == Operation.SQRT:
            return self.sqrt(a)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    
    def run_interactive(self) -> None:
        print("🧮 Advanced Object-Oriented Calculator")
        print("=" * 50)
        print("Operations:")
        print("1. Addition (+)")
        print("2. Subtraction (-)")
        print("3. Multiplication (×)")
        print("4. Division (÷)")
        print("5. Power (^)")
        print("6. Square Root (√)")
        print("7. View History")
        print("8. Clear History")
        print("9. Set Precision")
        print("0. Exit")
        print("=" * 50)
        
        while True:
            try:
                choice = input("\nSelect operation (0-9): ").strip()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    break
                
                if choice == '7':
                    self._display_history()
                    continue
                
                if choice == '8':
                    self.clear_history()
                    print("🗑️ History cleared!")
                    continue
                
                if choice == '9':
                    try:
                        precision = int(input("Enter decimal precision (0-10): "))
                        if 0 <= precision <= 10:
                            self.set_precision(precision)
                            print(f"📐 Precision set to {precision} decimal places")
                        else:
                            print("⚠️ Precision must be between 0 and 10")
                    except ValueError:
                        print("⚠️ Please enter a valid number")
                    continue
                
                if choice in ['1', '2', '3', '4', '5']:
                    try:
                        a = float(input("Enter first number: "))
                        b = float(input("Enter second number: "))
                    except ValueError:
                        print("⚠️ Please enter valid numbers")
                        continue
                    
                    if choice == '1':
                        result = self.add(a, b)
                    elif choice == '2':
                        result = self.subtract(a, b)
                    elif choice == '3':
                        result = self.multiply(a, b)
                    elif choice == '4':
                        result = self.divide(a, b)
                    elif choice == '5':
                        result = self.power(a, b)
                    
                    self._display_result(result)
                
                elif choice == '6':
                    try:
                        a = float(input("Enter number: "))
                        result = self.sqrt(a)
                        self._display_result(result)
                    except ValueError:
                        print("⚠️ Please enter a valid number")
                        continue
                
                else:
                    print("⚠️ Invalid choice! Please select 0-9")
                    
            except KeyboardInterrupt:
                print("\n👋 Calculator interrupted by user")
                break
            except Exception as e:
                print(f"⚠️ Unexpected error: {str(e)}")
    
    def _display_result(self, result: CalculationResult) -> None:
        if result.success:
            print(f"✅ {result.operation} = {result.result}")
        else:
            print(f"❌ {result.operation} → {result.result}")
    
    def _display_history(self) -> None:
        print("\n📊 Calculation History")
        print("=" * 50)
        if not self.history:
            print("📝 No calculations yet")
            return
        
        successful = self.get_successful_operations()
        failed = self.get_failed_operations()
        
        if successful:
            print("✅ Successful Operations:")
            for i, calc in enumerate(successful, 1):
                print(f"  {i}. {calc.operation} = {calc.result}")
        
        if failed:
            print("❌ Failed Operations:")
            for i, calc in enumerate(failed, 1):
                print(f"  {i}. {calc.operation} → {calc.result}")
        
        print(f"\n📈 Total: {len(self.history)} operations ({len(successful)} successful, {len(failed)} failed)")

if __name__ == "__main__":
    calculator = Calculator()
    calculator.run_interactive()

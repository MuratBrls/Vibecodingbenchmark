# -*- coding: utf-8 -*-
"""
Black Box Deep Analytics — Professional Validator v2.0
McCabe karmaşıklığı, PEP8 uyumu ve güvenlik analizi.
"""

import ast
import os
import re
import logging

from config import TARGETS, WATCHED_EXTENSIONS

logger = logging.getLogger("vibebench.validator_pro")

# ═══════════════════════════════════════════════════════════════════
#  GÜVENLİK TARAMASI
# ═══════════════════════════════════════════════════════════════════

DANGEROUS_PATTERNS = [
    (r'\beval\s*\(', "eval() kullanımı"),
    (r'\bexec\s*\(', "exec() kullanımı"),
    (r'\bos\.system\s*\(', "os.system() kullanımı"),
    (r'\bsubprocess\.call\s*\(', "subprocess.call() — shell injection riski"),
    (r'\bsubprocess\.Popen\s*\(.*shell\s*=\s*True', "subprocess.Popen(shell=True)"),
    (r'\b__import__\s*\(', "Dinamik __import__() kullanımı"),
    (r'\bpickle\.loads?\s*\(', "pickle deserialization riski"),
    (r'\byaml\.load\s*\((?!.*Loader)', "yaml.load() — güvensiz (Loader belirtilmemiş)"),
    (r'\binput\s*\(.*\)\s*$', "input() — kullanıcıdan veri alma (potansiyel risk)"),
]


def _scan_security(filepath: str) -> list:
    """Dosyayı tehlikeli çağrılar için tarar."""
    issues = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for pattern, desc in DANGEROUS_PATTERNS:
                    if re.search(pattern, line):
                        issues.append({
                            "file": os.path.basename(filepath),
                            "line": lineno,
                            "issue": desc,
                            "code": stripped[:100],
                        })
    except Exception as e:
        logger.warning("Güvenlik taraması hatası (%s): %s", filepath, e)
    return issues


# ═══════════════════════════════════════════════════════════════════
#  McCABE KARMAŞIKLIĞI
# ═══════════════════════════════════════════════════════════════════

def _calculate_mccabe(filepath: str) -> dict:
    """
    Python dosyasının McCabe cyclomatic complexity'sini hesaplar.

    Returns:
        {"avg_complexity": float, "max_complexity": int, "functions": list}
    """
    result = {"avg_complexity": 0.0, "max_complexity": 0, "functions": []}

    if not filepath.endswith(".py"):
        return result

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()

        tree = ast.parse(source)
        complexities = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = _node_complexity(node)
                complexities.append(complexity)
                result["functions"].append({
                    "name": node.name,
                    "complexity": complexity,
                    "line": node.lineno,
                })

        if complexities:
            result["avg_complexity"] = round(sum(complexities) / len(complexities), 2)
            result["max_complexity"] = max(complexities)

    except SyntaxError:
        logger.debug("McCabe: syntax error — %s", filepath)
    except Exception as e:
        logger.warning("McCabe hesaplama hatası (%s): %s", filepath, e)

    return result


def _node_complexity(node) -> int:
    """Bir AST node'unun cyclomatic complexity'sini hesaplar."""
    complexity = 1  # Base complexity
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.IfExp)):
            complexity += 1
        elif isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, (ast.And, ast.Or)):
            complexity += 1
        elif isinstance(child, ast.Assert):
            complexity += 1
        elif isinstance(child, ast.comprehension):
            complexity += 1
    return complexity


# ═══════════════════════════════════════════════════════════════════
#  PEP8 UYUMU
# ═══════════════════════════════════════════════════════════════════

def _check_pep8(filepath: str) -> dict:
    """
    PEP8 uyumluluğunu kontrol eder.

    Returns:
        {"total_errors": int, "compliance_pct": float, "error_types": dict}
    """
    result = {"total_errors": 0, "compliance_pct": 100.0, "error_types": {}}

    if not filepath.endswith(".py"):
        return result

    try:
        import pycodestyle
        style = pycodestyle.StyleGuide(quiet=True, max_line_length=120)
        check = style.check_files([filepath])
        total_errors = check.get_count()

        # Satır sayısına göre uyum yüzdesi hesapla
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            total_lines = sum(1 for _ in f)

        if total_lines > 0:
            compliance = max(0.0, 100.0 - (total_errors / total_lines * 100.0))
        else:
            compliance = 100.0

        result["total_errors"] = total_errors
        result["compliance_pct"] = round(compliance, 1)

    except ImportError:
        logger.warning("pycodestyle yüklü değil — PEP8 kontrolü atlanıyor")
        result["compliance_pct"] = -1  # Bilinmiyor
    except Exception as e:
        logger.warning("PEP8 kontrolü hatası (%s): %s", filepath, e)

    return result


# ═══════════════════════════════════════════════════════════════════
#  BİRLEŞİK ANALİZ
# ═══════════════════════════════════════════════════════════════════

def analyze_pro(tool_name: str) -> dict:
    """
    Bir aracın tüm kaynak dosyalarını profesyonel düzeyde analiz eder.

    Returns:
        {
            "mccabe_avg": float,
            "mccabe_max": int,
            "pep8_compliance": float,
            "pep8_errors": int,
            "security_issues": list,
            "security_count": int,
            "clean_code_score": float,   # 0-100 birleşik temiz kod puanı
        }
    """
    target_dir = TARGETS.get(tool_name, "")
    if not target_dir or not os.path.isdir(target_dir):
        return _empty_result()

    all_mccabe = []
    all_pep8_errors = 0
    all_pep8_lines = 0
    all_security = []

    for root, _, files in os.walk(target_dir):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext.lower() not in WATCHED_EXTENSIONS:
                continue

            filepath = os.path.join(root, fname)

            # McCabe (sadece Python)
            if ext == ".py":
                mc = _calculate_mccabe(filepath)
                if mc["functions"]:
                    all_mccabe.extend([f["complexity"] for f in mc["functions"]])

                # PEP8 (sadece Python)
                pep = _check_pep8(filepath)
                all_pep8_errors += pep["total_errors"]
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        all_pep8_lines += sum(1 for _ in f)
                except Exception:
                    pass

            # Güvenlik (tüm dosyalar)
            sec = _scan_security(filepath)
            all_security.extend(sec)

    # Hesaplamalar
    avg_mccabe = round(sum(all_mccabe) / len(all_mccabe), 2) if all_mccabe else 0.0
    max_mccabe = max(all_mccabe) if all_mccabe else 0

    if all_pep8_lines > 0:
        pep8_compliance = round(max(0.0, 100.0 - (all_pep8_errors / all_pep8_lines * 100.0)), 1)
    else:
        pep8_compliance = 100.0

    # Temiz Kod Puanı (0-100)
    # McCabe: düşük = iyi (1-5 ideal, 10+ kötü)
    mccabe_score = max(0, 100 - max(0, (avg_mccabe - 3)) * 10) if avg_mccabe > 0 else 50
    # PEP8: yüzde olarak zaten 0-100
    pep8_score = pep8_compliance if pep8_compliance >= 0 else 50
    # Güvenlik: her issue -15 puan
    security_score = max(0, 100 - len(all_security) * 15)

    clean_code_score = round(mccabe_score * 0.35 + pep8_score * 0.35 + security_score * 0.30, 1)

    return {
        "mccabe_avg": avg_mccabe,
        "mccabe_max": max_mccabe,
        "pep8_compliance": pep8_compliance,
        "pep8_errors": all_pep8_errors,
        "security_issues": all_security,
        "security_count": len(all_security),
        "clean_code_score": min(100.0, clean_code_score),
    }


def _empty_result() -> dict:
    return {
        "mccabe_avg": 0.0,
        "mccabe_max": 0,
        "pep8_compliance": 0.0,
        "pep8_errors": 0,
        "security_issues": [],
        "security_count": 0,
        "clean_code_score": 0.0,
    }

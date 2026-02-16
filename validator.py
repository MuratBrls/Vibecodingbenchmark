# -*- coding: utf-8 -*-
"""
VibeBench Validation & Deep Design Analysis v1.1
Syntax kontrolü + import analizi + mimari tespit + karmaşıklık analizi.
"""

import ast
import os
import subprocess
import glob
import logging
import re

from config import TARGETS, WATCHED_EXTENSIONS, SUBPROCESS_TIMEOUT

logger = logging.getLogger("vibebench.validator")


# ═══════════════════════════════════════════════════════════════════
#  DOSYA TARAMA
# ═══════════════════════════════════════════════════════════════════

def _find_source_files(target_dir: str) -> list:
    files = []
    try:
        for ext in WATCHED_EXTENSIONS:
            files.extend(glob.glob(os.path.join(target_dir, f"**/*{ext}"), recursive=True))
    except Exception as e:
        logger.error("Dosya tarama hatası (%s): %s", target_dir, e)
    return files


# ═══════════════════════════════════════════════════════════════════
#  SYNTAX KONTROLÜ
# ═══════════════════════════════════════════════════════════════════

def validate_python_syntax(filepath: str) -> dict:
    result = {"syntax_ok": False, "error_message": None}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        ast.parse(source, filename=filepath)
        result["syntax_ok"] = True
    except SyntaxError as e:
        result["error_message"] = f"SyntaxError: {e.msg} (satır {e.lineno})"
    except Exception as e:
        result["error_message"] = f"Okuma hatası: {e}"
    return result


def validate_js_syntax(filepath: str) -> dict:
    result = {"syntax_ok": False, "error_message": None}
    try:
        proc = subprocess.run(
            ["node", "--check", filepath],
            capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT,
        )
        if proc.returncode == 0:
            result["syntax_ok"] = True
        else:
            result["error_message"] = proc.stderr.strip()[:200]
    except FileNotFoundError:
        result["syntax_ok"] = True
        result["error_message"] = "Node.js bulunamadı — atlandı"
    except subprocess.TimeoutExpired:
        result["error_message"] = "Syntax kontrol timeout"
    except Exception as e:
        result["error_message"] = str(e)[:200]
    return result


def run_script(filepath: str) -> dict:
    result = {"runtime_ok": False, "output": None, "error_message": None}
    _, ext = os.path.splitext(filepath)
    cmd_map = {".py": ["python", filepath], ".js": ["node", filepath]}
    cmd = cmd_map.get(ext.lower())
    if cmd is None:
        result["runtime_ok"] = True
        result["error_message"] = "Otomatik çalıştırılamayan dosya türü"
        return result
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=SUBPROCESS_TIMEOUT, cwd=os.path.dirname(filepath),
        )
        result["output"] = (proc.stdout.strip()[:500]) if proc.stdout else None
        if proc.returncode == 0:
            result["runtime_ok"] = True
        else:
            result["error_message"] = (proc.stderr.strip()[:300]) if proc.stderr else f"Exit code: {proc.returncode}"
    except FileNotFoundError:
        result["error_message"] = f"Çalıştırıcı bulunamadı: {cmd[0]}"
    except subprocess.TimeoutExpired:
        result["error_message"] = f"Runtime timeout ({SUBPROCESS_TIMEOUT}sn)"
    except Exception as e:
        result["error_message"] = str(e)[:200]
    return result


def validate_file(filepath: str) -> dict:
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    if ext == ".py":
        syntax = validate_python_syntax(filepath)
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        syntax = validate_js_syntax(filepath)
    else:
        syntax = {"syntax_ok": True, "error_message": None}

    if syntax["syntax_ok"] and ext in (".py", ".js"):
        runtime = run_script(filepath)
    else:
        runtime = {"runtime_ok": syntax["syntax_ok"], "output": None,
                    "error_message": syntax.get("error_message")}
    return {
        "file": os.path.basename(filepath),
        "syntax_ok": syntax["syntax_ok"],
        "runtime_ok": runtime.get("runtime_ok", False),
        "error_message": syntax.get("error_message") or runtime.get("error_message"),
    }


def validate_tool(tool_name: str) -> list:
    target_dir = TARGETS.get(tool_name)
    if not target_dir or not os.path.isdir(target_dir):
        return []
    results = []
    for f in _find_source_files(target_dir):
        try:
            results.append(validate_file(f))
        except Exception as e:
            results.append({"file": os.path.basename(f), "syntax_ok": False,
                            "runtime_ok": False, "error_message": str(e)[:200]})
    return results


# ═══════════════════════════════════════════════════════════════════
#  DERİN TASARIM ANALİZİ (Python dosyaları için)
# ═══════════════════════════════════════════════════════════════════

def _analyze_python_ast(filepath: str) -> dict:
    """Python dosyasını AST ile analiz eder."""
    analysis = {
        "imports": [],
        "architecture": "Scripting",
        "num_functions": 0,
        "num_classes": 0,
        "max_loop_depth": 0,
        "complexity_score": 0,
    }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
        logger.warning("AST analiz hatası (%s): %s", filepath, e)
        return analysis

    # ── Import Analizi ──────────────────────────────────────────
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in analysis["imports"]:
                    analysis["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module and module not in analysis["imports"]:
                analysis["imports"].append(module)

    # ── Fonksiyon ve Sınıf Sayısı ───────────────────────────────
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            analysis["num_functions"] += 1
        elif isinstance(node, ast.ClassDef):
            analysis["num_classes"] += 1
            # Sınıf içindeki methodlar
            for child in ast.walk(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    analysis["num_functions"] += 1

    # ── Döngü Derinliği ────────────────────────────────────────
    analysis["max_loop_depth"] = _calc_max_loop_depth(tree)

    # ── Mimari Tespit ──────────────────────────────────────────
    if analysis["num_classes"] >= 1:
        analysis["architecture"] = "OOP"
    elif analysis["num_functions"] >= 2:
        analysis["architecture"] = "Functional"
    else:
        analysis["architecture"] = "Scripting"

    # ── Karmaşıklık Skoru (0-100) ──────────────────────────────
    # Fonksiyon: daha fazla = daha iyi yapılandırılmış
    func_score = min(analysis["num_functions"] * 10, 40)
    # OOP bonus
    class_score = min(analysis["num_classes"] * 15, 30)
    # Import çeşitliliği
    import_score = min(len(analysis["imports"]) * 5, 20)
    # Döngü derinliği cezası (>3 kötü)
    depth_penalty = max(0, (analysis["max_loop_depth"] - 3) * 5)

    analysis["complexity_score"] = min(100, func_score + class_score + import_score - depth_penalty)

    return analysis


def _calc_max_loop_depth(node, current_depth=0) -> int:
    """AST ağacında maksimum döngü derinliğini hesaplar."""
    max_depth = current_depth
    try:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
                child_depth = _calc_max_loop_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = _calc_max_loop_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)
    except Exception:
        pass
    return max_depth


def _analyze_js_basic(filepath: str) -> dict:
    """JavaScript dosyası için basit regex-tabanlı analiz."""
    analysis = {
        "imports": [],
        "architecture": "Scripting",
        "num_functions": 0,
        "num_classes": 0,
        "max_loop_depth": 0,
        "complexity_score": 0,
    }
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()

        # Import/require
        for m in re.findall(r'(?:import\s+.*?from\s+["\'](.+?)["\']|require\s*\(\s*["\'](.+?)["\']\s*\))', source):
            mod = m[0] or m[1]
            if mod and mod not in analysis["imports"]:
                analysis["imports"].append(mod)

        # Fonksiyon sayısı
        analysis["num_functions"] = len(re.findall(r'(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_]\w*)\s*=>)', source))

        # Sınıf sayısı
        analysis["num_classes"] = len(re.findall(r'\bclass\s+\w+', source))

        # Mimari
        if analysis["num_classes"] >= 1:
            analysis["architecture"] = "OOP"
        elif analysis["num_functions"] >= 2:
            analysis["architecture"] = "Functional"

        func_score = min(analysis["num_functions"] * 10, 40)
        class_score = min(analysis["num_classes"] * 15, 30)
        import_score = min(len(analysis["imports"]) * 5, 20)
        analysis["complexity_score"] = min(100, func_score + class_score + import_score)

    except Exception as e:
        logger.warning("JS analiz hatası (%s): %s", filepath, e)

    return analysis


def analyze_design(filepath: str) -> dict:
    """Dosya türüne göre derin tasarım analizi yapar."""
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()

    if ext == ".py":
        return _analyze_python_ast(filepath)
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        return _analyze_js_basic(filepath)
    else:
        return {
            "imports": [], "architecture": "N/A",
            "num_functions": 0, "num_classes": 0,
            "max_loop_depth": 0, "complexity_score": 0,
        }


def analyze_tool_design(tool_name: str) -> dict:
    """
    Bir aracın tüm kaynak dosyalarını analiz edip birleştirilmiş rapor üretir.

    Returns:
        {
            "all_imports": list,
            "architecture": str,           # OOP / Functional / Scripting
            "total_functions": int,
            "total_classes": int,
            "max_loop_depth": int,
            "avg_complexity": float,        # 0-100
            "file_analyses": list[dict],
        }
    """
    target_dir = TARGETS.get(tool_name)
    if not target_dir or not os.path.isdir(target_dir):
        return {"all_imports": [], "architecture": "N/A", "total_functions": 0,
                "total_classes": 0, "max_loop_depth": 0, "avg_complexity": 0,
                "file_analyses": []}

    all_imports = []
    total_funcs = 0
    total_classes = 0
    max_depth = 0
    scores = []
    file_analyses = []

    for f in _find_source_files(target_dir):
        try:
            a = analyze_design(f)
            file_analyses.append({"file": os.path.basename(f), **a})

            for imp in a["imports"]:
                if imp not in all_imports:
                    all_imports.append(imp)

            total_funcs += a["num_functions"]
            total_classes += a["num_classes"]
            max_depth = max(max_depth, a["max_loop_depth"])
            scores.append(a["complexity_score"])
        except Exception as e:
            logger.warning("Tasarım analiz hatası (%s): %s", f, e)

    avg_complexity = round(sum(scores) / len(scores), 1) if scores else 0

    # Genel mimari tespit
    if total_classes >= 1:
        arch = "OOP"
    elif total_funcs >= 2:
        arch = "Functional"
    else:
        arch = "Scripting"

    return {
        "all_imports": all_imports,
        "architecture": arch,
        "total_functions": total_funcs,
        "total_classes": total_classes,
        "max_loop_depth": max_depth,
        "avg_complexity": avg_complexity,
        "file_analyses": file_analyses,
    }


# ═══════════════════════════════════════════════════════════════════
#  YARDIMCI
# ═══════════════════════════════════════════════════════════════════

def count_lines(target_dir: str) -> int:
    total = 0
    for f in _find_source_files(target_dir):
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                total += sum(1 for _ in fh)
        except Exception:
            pass
    return total


def get_total_file_size(target_dir: str) -> int:
    total = 0
    for f in _find_source_files(target_dir):
        try:
            total += os.path.getsize(f)
        except Exception:
            pass
    return total

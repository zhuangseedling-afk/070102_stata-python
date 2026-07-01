"""沙箱安全策略"""
# 禁用危险模块/函数
BLOCKED_MODULES = {
    "os", "subprocess", "sys", "shutil", "socket", "requests",
    "urllib", "http", "ftplib", "telnetlib", "smtplib",
    "pickle", "marshal", "ctypes", "multiprocessing",
}

BLOCKED_BUILTINS = {
    "__import__", "eval", "exec", "compile", "open",
    "input", "globals", "locals", "vars",
}

# 允许的 safe 模块
ALLOWED_MODULES = {
    "numpy", "scipy", "statsmodels", "matplotlib",
    "math", "statistics", "random", "collections",
    "itertools", "functools", "json", "csv",
    "warnings", "copy", "typing", "dataclasses",
    "enum", "re", "string", "datetime", "decimal",
    "fractions", "operator", "hashlib",
}


def create_sandbox_globals() -> dict:
    """创建安全的全局命名空间"""
    safe_globals = {
        "__builtins__": {
            # 基础类型
            "int": int, "float": float, "str": str, "bool": bool,
            "list": list, "dict": dict, "tuple": tuple, "set": set,
            "len": len, "range": range, "enumerate": enumerate,
            "zip": zip, "map": map, "filter": filter,
            "min": min, "max": max, "sum": sum, "abs": abs,
            "round": round, "sorted": sorted, "reversed": reversed,
            "type": type, "isinstance": isinstance, "hasattr": hasattr,
            "print": print, "format": format,
            "ValueError": ValueError, "TypeError": TypeError,
            "KeyError": KeyError, "IndexError": IndexError,
            "ZeroDivisionError": ZeroDivisionError,
            "Exception": Exception, "ImportError": ImportError,
            "True": True, "False": False, "None": None,
            "complex": complex, "pow": pow, "divmod": divmod,
            "slice": slice, "any": any, "all": all,
            "open": print,  # 禁用 open, 重定向到 print
        }
    }
    return safe_globals
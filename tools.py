"""工具层：助手可以调用的实用功能（function calling）。"""
import ast
import datetime
import operator


# ---- 工具函数 ----

def get_time():
    """获取当前日期和时间。"""
    now = datetime.datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return now.strftime("%Y年%m月%d日 %H:%M") + " " + weekdays[now.weekday()]


def calculate(expression):
    """安全地计算数学表达式（只用 ast，不用 eval）。"""
    _ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ops:
            return _ops[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ops:
            return _ops[type(node.op)](_eval(node.operand))
        raise ValueError("不支持的表达式")

    try:
        result = _eval(ast.parse(expression, mode="eval"))
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return str(result)
    except Exception:
        return "无法计算"


# ---- 工具定义（给模型的 function calling schema）----

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取当前日期和时间。当用户问'现在几点'、'今天几号'、'今天星期几'时调用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式。当用户问计算题、算数时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "要计算的数学表达式，如 '3*4+5' 或 '100除以4'"},
                },
                "required": ["expression"],
            },
        },
    },
]


def run_tool(name, arguments):
    """执行指定工具，返回结果字符串。"""
    if name == "get_time":
        return get_time()
    if name == "calculate":
        return calculate(arguments.get("expression", ""))
    return "未知工具"

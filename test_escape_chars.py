#!/usr/bin/env python3
"""
测试控制台转义字符解析功能
"""

import re

def parse_arguments(args_str: str):
    """
    解析参数字符串（复制自 console_handler.py）
    """
    arguments = {}
    
    if not args_str.strip():
        return arguments
    
    # 匹配 key="value" 或 key=value
    # 使用 (?:\\.|[^"])* 来匹配：要么是转义序列 \. ，要么是非引号字符
    pattern = r'(\w+)=(?:"((?:\\.|[^"])*)"|\'((?:\\.|[^\'])*)\'|([^\s]+))'
    matches = re.findall(pattern, args_str)
    
    for match in matches:
        key = match[0]
        value = match[1] or match[2] or match[3]
        
        # 处理转义字符
        if isinstance(value, str):
            value = value.replace('\\n', '\n')
            value = value.replace('\\t', '\t')
            value = value.replace('\\r', '\r')
            value = value.replace('\\\\', '\\')
            value = value.replace('\\"', '"')
            value = value.replace("\\'", "'")
        
        arguments[key] = value
    
    return arguments


def test_escape_chars():
    """测试转义字符解析"""
    
    print("=" * 60)
    print("测试转义字符解析功能")
    print("=" * 60)
    print()
    
    # 测试用例
    test_cases = [
        {
            "input": 'content="# 标题\\n\\n这是内容"',
            "expected": "# 标题\n\n这是内容",
            "desc": "测试 \\n 换行符"
        },
        {
            "input": 'content="第一部分\\n\\n第二部分\\n第三部分"',
            "expected": "第一部分\n\n第二部分\n第三部分",
            "desc": "测试多个 \\n"
        },
        {
            "input": 'content="他说\\"这很重要\\""',
            "expected": '他说"这很重要"',
            "desc": "测试 \\\" 引号转义"
        },
        {
            "input": 'content="路径：C:\\\\Users\\\\Documents"',
            "expected": "路径：C:\\Users\\Documents",
            "desc": "测试 \\\\ 反斜杠转义"
        },
        {
            "input": 'content="列表：\\n\\t- 项目1\\n\\t- 项目2"',
            "expected": "列表：\n\t- 项目1\n\t- 项目2",
            "desc": "测试 \\t 制表符"
        }
    ]
    
    # 执行测试
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"测试 {i}: {test['desc']}")
        print(f"输入: {test['input']}")
        
        result = parse_arguments(test['input'])
        actual = result.get('content', '')
        expected = test['expected']
        
        # 比较结果
        if actual == expected:
            print("✅ 通过")
            passed += 1
        else:
            print("❌ 失败")
            print(f"期望: {repr(expected)}")
            print(f"实际: {repr(actual)}")
            failed += 1
        
        print()
    
    # 总结
    print("=" * 60)
    print(f"测试总结: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = test_escape_chars()
    exit(0 if success else 1)


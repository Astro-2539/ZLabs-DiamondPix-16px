# -*- coding: utf-8 -*-
"""
Kbitx XML文件比较工具
比较两个.kbitx文件，提取差异的"g"元素并生成新的XML文件
"""

import xml.etree.ElementTree as ET
from typing import Dict, Optional, Set, Tuple
import sys
import argparse


def parse_kbitx_file(filepath: str) -> Tuple[Optional[ET.Element], Dict[str, ET.Element], list]:
    """
    解析.kbitx文件，提取根元素和所有g元素
    
    Args:
        filepath: 文件路径
        
    Returns:
        tuple: (根元素, g元素字典{u: element}, 所有子元素列表)
    """
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # 提取所有g元素，以u属性为键
        g_elements = {}
        all_children = list(root)
        
        for child in root:
            if child.tag == 'g':
                u_value = child.get('u')
                if u_value is not None:
                    g_elements[u_value] = child
        
        return root, g_elements, all_children
        
    except ET.ParseError as e:
        print(f"错误: 无法解析文件 {filepath}: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"错误: 文件不存在: {filepath}")
        sys.exit(1)


def compare_g_elements(g_a: Dict[str, ET.Element], g_b: Dict[str, ET.Element]) -> Set[str]:
    """
    比较两个字典中的g元素，返回需要保留的u属性集合
    
    Args:
        g_a: 文件A中的g元素字典 {u: element}
        g_b: 文件B中的g元素字典 {u: element}
        
    Returns:
        set: 需要保留的u属性值集合
    """
    diff_u_values = set()
    
    for u_value, element_b in g_b.items():
        # 情况①: B中有但A中没有
        if u_value not in g_a:
            diff_u_values.add(u_value)
        else:
            # 情况②: 都有但d属性不同
            element_a = g_a[u_value]
            d_a = element_a.get('d', '')
            d_b = element_b.get('d', '')
            
            if d_a != d_b:
                diff_u_values.add(u_value)
    
    return diff_u_values


def format_element_to_string(element: ET.Element) -> str:
    """
    将元素格式化为XML字符串（自闭合标签格式）
    
    Args:
        element: XML元素
        
    Returns:
        str: 格式化的XML字符串
    """
    # 按特定顺序排列属性：u, x, y, w, d
    attrs = []
    attr_order = ['u', 'x', 'y', 'w', 'd']
    
    for attr in attr_order:
        value = element.get(attr)
        if value is not None:
            # 处理需要转义的字符
            escaped_value = (value
                           .replace('&', '&amp;')
                           .replace('<', '&lt;')
                           .replace('>', '&gt;')
                           .replace('"', '&quot;'))
            attrs.append(f'{attr}="{escaped_value}"')
    
    # 添加其他未在顺序列表中的属性
    for attr, value in element.attrib.items():
        if attr not in attr_order and value is not None:
            escaped_value = (value
                           .replace('&', '&amp;')
                           .replace('<', '&lt;')
                           .replace('>', '&gt;')
                           .replace('"', '&quot;'))
            attrs.append(f'{attr}="{escaped_value}"')
    
    if attrs:
        return f'<g {" ".join(attrs)}/>'
    else:
        return '<g/>'


def write_output_file(output_path: str, root_b_children: list, diff_u_values: Set[str], g_b: Dict[str, ET.Element]):
    """
    写入输出文件
    
    Args:
        output_path: 输出文件路径
        root_b_children: 文件B的所有子元素
        diff_u_values: 需要保留的u值集合
        g_b: 文件B的g元素字典
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入XML声明和DOCTYPE
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<!DOCTYPE kbits PUBLIC "-//Kreative//DTD BitsNPicasBitmap 1.0//EN" "http://www.kreativekorp.com/dtd/kbitx.dtd">\n')
            
            # 写入根元素开始标签
            f.write('<kbits>\n')
            
            # 复制B文件中的所有prop和name元素
            for child in root_b_children:
                if child.tag in ['prop', 'name']:
                    # 将元素转换为字符串
                    elem_str = ET.tostring(child, encoding='unicode')
                    # 确保自闭合格式正确
                    if not elem_str.endswith('/>') and '</' + child.tag + '>' not in elem_str:
                        elem_str = elem_str.replace(f'></{child.tag}>', '/>')
                    f.write(elem_str + '\n')
            
            # 写入差异的g元素
            for u_value in sorted(diff_u_values, key=lambda x: int(x) if x.isdigit() else x):
                if u_value in g_b:
                    g_str = format_element_to_string(g_b[u_value])
                    f.write(g_str + '\n')
            
            # 写入根元素结束标签
            f.write('</kbits>\n')
            
        print(f"成功: 差异文件已保存至 {output_path}")
        print(f"统计: 共发现 {len(diff_u_values)} 个差异的g元素")
        
    except IOError as e:
        print(f"错误: 无法写入文件 {output_path}: {e}")
        sys.exit(1)


def main():
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(
        description='比较两个.kbitx文件，提取差异的g元素',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python kbitx_compare.py old.kbitx new.kbitx diff.kbitx
  python kbitx_compare.py -a fileA.kbitx -b fileB.kbitx -o output.kbitx
        '''
    )
    
    parser.add_argument('file_a', nargs='?', help='原始文件A（旧版本）')
    parser.add_argument('file_b', nargs='?', help='对比文件B（新版本）')
    parser.add_argument('output', nargs='?', help='输出文件路径')
    parser.add_argument('-a', '--original', help='原始文件A路径')
    parser.add_argument('-b', '--modified', help='对比文件B路径')
    parser.add_argument('-o', '--output', dest='output_file', help='输出文件路径')
    
    args = parser.parse_args()
    
    # 确定文件路径
    file_a = args.original or args.file_a
    file_b = args.modified or args.file_b
    output_file = args.output_file or args.output
    
    # 验证参数
    if not all([file_a, file_b, output_file]):
        parser.print_help()
        sys.exit(1)
    
    print(f"正在比较文件...")
    print(f"  原始文件(A): {file_a}")
    print(f"  对比文件(B): {file_b}")
    print(f"  输出文件: {output_file}")
    print()
    
    # 解析两个文件
    root_a, g_a, children_a = parse_kbitx_file(file_a)
    root_b, g_b, children_b = parse_kbitx_file(file_b)
    
    print(f"文件A统计: 共 {len(g_a)} 个g元素")
    print(f"文件B统计: 共 {len(g_b)} 个g元素")
    print()
    
    # 比较g元素
    diff_u_values = compare_g_elements(g_a, g_b)
    
    # 分类统计
    new_in_b = [u for u in diff_u_values if u not in g_a]
    modified_in_b = [u for u in diff_u_values if u in g_a]
    
    print(f"差异分析:")
    print(f"  - B文件独有: {len(new_in_b)} 个")
    print(f"  - d属性不同: {len(modified_in_b)} 个")
    print()
    
    # 写入输出文件
    write_output_file(output_file, children_b, diff_u_values, g_b)


if __name__ == '__main__':
    main()
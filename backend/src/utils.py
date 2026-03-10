"""
通用工具函数
包含确定性的工具逻辑，不需要LLM参与
"""

import os
import shutil
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from rich.console import Console

from config import PAGES_DIR, RESULTS_DIR, ALLOWED_EXTENSIONS

load_dotenv()
console = Console()


def prepare_input(file_path: str) -> List[str]:
    """
    步骤1: 准备输入文件

    验证文件格式，将文件复制到 PAGES_DIR 统一管理。
    PDF 和图片均直接保留原始格式，由 PaddleOCR API 统一处理。

    Args:
        file_path: 输入文件路径 (PDF或图片文件)

    Returns:
        List[str]: 标准化后的文件路径列表（单个文件返回单元素列表）

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的文件格式
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    pages_dir = PAGES_DIR
    os.makedirs(pages_dir, exist_ok=True)

    file_ext = Path(file_path).suffix.lower()
    file_stem = Path(file_path).stem

    supported_exts = {f".{ext}" for ext in ALLOWED_EXTENSIONS}
    if file_ext not in supported_exts:
        raise ValueError(
            f"不支持的文件格式: {file_ext}\n"
            f"支持的格式: {', '.join(sorted(supported_exts))}"
        )

    console.print(f"[cyan]正在处理文件: {file_path}[/cyan]")

    output_path = os.path.join(pages_dir, f"{file_stem}{file_ext}")
    shutil.copy2(file_path, output_path)
    console.print(f"[green]  ✓ 文件已复制: {output_path}[/green]")

    return [output_path]


def export_wrongbook(
    questions: List[Dict[str, Any]],
    selected_ids: List[str],
    output_path: str = None,
    batch_info: Dict[str, Any] = None
) -> str:
    """
    步骤5: 导出错题本

    将用户选择的题目导出为Markdown格式的错题本，并可选入库到数据库

    Args:
        questions: 题目列表
        selected_ids: 用户选择的题目ID列表
        output_path: 输出Markdown文件路径（可选）
        batch_info: 批次信息（用于入库），包含 original_filename, subject 等

    Returns:
        str: 导出的Markdown文件路径
    """
    if output_path is None:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        output_path = os.path.join(RESULTS_DIR, "wrongbook.md")

    # 过滤选中的题目
    selected_questions = [q for q in questions if q.get('question_id') in selected_ids]

    # 构建Markdown内容
    md_content = "# 错题本\n\n"
    md_content += f"> 共收录 {len(selected_questions)} 道题目\n\n"
    md_content += "---\n\n"

    for i, q in enumerate(selected_questions, start=1):
        md_content += f"## {i}. 题目 {q.get('question_id', '')} ({q.get('question_type', '未知')})\n\n"

        # 获取图片引用列表，用于填充空的 image block
        image_refs = q.get('image_refs') or []
        rendered_images = set()  # 记录已渲染的图片路径

        # 添加内容块（只有 text 和 image，公式以 LaTeX 标记嵌入 text 中）
        for block in q.get('content_blocks', []):
            if block['block_type'] == 'text':
                md_content += f"{block['content']}\n\n"
            elif block['block_type'] == 'image':
                image_path = block.get('content', '').strip()
                if image_path:
                    rendered_images.add(image_path)

                # 将 Flask 路由路径转为 Markdown 相对路径
                if image_path.startswith("/images/"):
                    from config import STRUCT_DIR
                    rel_struct_dir = os.path.relpath(STRUCT_DIR, RESULTS_DIR)
                    image_path = f"{rel_struct_dir}/imgs/{image_path[len('/images/') :]}"

                if image_path:
                    md_content += f"![图片]({image_path})\n\n"

        # 添加选项
        if q.get('options'):
            for option in q['options']:
                md_content += f"{option}\n\n"

        # 兜底：渲染 image_refs 中未被 content_blocks 覆盖的图片
        remaining_images = [p for p in image_refs if p not in rendered_images]
        if remaining_images:
            for image_path in remaining_images:
                if image_path.startswith("/images/"):
                    from config import STRUCT_DIR
                    rel_struct_dir = os.path.relpath(STRUCT_DIR, RESULTS_DIR)
                    image_path = f"{rel_struct_dir}/imgs/{image_path[len('/images/') :]}"
                md_content += f"![图片]({image_path})\n\n"

        md_content += "### 我的答案\n\n"
        md_content += "_（请在此处填写你的答案）_\n\n"

        md_content += "### 正确答案\n\n"
        md_content += "_（请在此处填写正确答案）_\n\n"

        md_content += "### 解析\n\n"
        md_content += "_（请在此处填写解题思路和知识点）_\n\n"

        md_content += "---\n\n"

    # 保存Markdown
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    console.print(f"[green]✓ 错题本已导出: {output_path}[/green]")

    return output_path


def simplify_ocr_results(ocr_results: list) -> List[Dict[str, Any]]:
    """简化 OCR 结果，只保留 split 所需字段

    将 PaddleOCR API 原始返回结果精简为 block_label、block_content、block_order 三个字段。
    供 workflow 和 retry_ocr 共享使用。

    Args:
        ocr_results: PaddleOCR API 原始返回结果列表

    Returns:
        简化后的 OCR 数据列表，每项包含 page_index 和 blocks
    """
    simplified = []
    page_index = 0
    for result in ocr_results:
        if "layoutParsingResults" not in result:
            continue
        for page in result["layoutParsingResults"]:
            if "prunedResult" not in page:
                continue
            parsing_res = page["prunedResult"].get("parsing_res_list", [])
            slim_blocks = []
            # block_label 归一化映射：OCR API 可能返回新标签，统一转为已知类型
            _label_normalize = {
                "display_formula": "formula",
                "number": "text",
            }
            for b in parsing_res:
                content = b.get("block_content", "")
                label = _label_normalize.get(b.get("block_label", ""), b.get("block_label", ""))
                if label in ("image", "chart") and not content:
                    bbox = b.get("block_bbox")
                    if bbox:
                        prefix = "img_in_chart_box" if label == "chart" else "img_in_image_box"
                        content = f"/images/{prefix}_{int(bbox[0])}_{int(bbox[1])}_{int(bbox[2])}_{int(bbox[3])}.jpg"
                slim_blocks.append({
                    "block_label": label,
                    "block_content": content,
                    "block_order": b.get("block_order"),
                })
            simplified.append({
                "page_index": page_index,
                "blocks": slim_blocks,
            })
            page_index += 1
    return simplified


def run_async(coro):
    """在同步上下文中运行异步协程（兼容已有事件循环）

    如果当前线程已有 running 事件循环（如在 Flask/Jupyter 中），
    则在新线程中创建事件循环运行；否则直接 asyncio.run。

    Args:
        coro: 异步协程对象

    Returns:
        协程返回值
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)

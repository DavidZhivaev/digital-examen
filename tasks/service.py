import hashlib
import uuid
from fastapi import HTTPException
from tortoise.transactions import in_transaction
from tasks.models import TaskBank, TaskPosition, Task
import os
import shutil
from docx import Document
from lxml import etree
from pathlib import Path
from marker.convert import convert_single_pdf
from marker.models import load_all_models

def stable_hash(bank_id: int, task_id: uuid.UUID) -> int:
    key = f"{bank_id}:{str(task_id)}"
    return int(hashlib.md5(key.encode()).hexdigest(), 16)


async def reorder_positions(bank: TaskBank, new_order: list[int]):
    async with in_transaction():
        positions = await bank.positions.all()
        pos_map = {p.id: p for p in positions}
        
        if len(new_order) != len(positions) or set(new_order) != set(pos_map.keys()):
            raise HTTPException(400, "Передан некорректный список ID для сортировки")

        for p in positions:
            p.order = p.order + 10000
            await p.save()

        for idx, pos_id in enumerate(new_order, start=1):
            pos = pos_map[pos_id]
            pos.order = idx
            await pos.save()


class TaskVisibilityService:
    @staticmethod
    async def get_user_context(user, subject) -> tuple[bool, bool, bool]:
        is_operator = user.role >= 3
        is_admin = await subject.admins.filter(id=user.id).exists()
        is_teacher = await subject.teachers.filter(id=user.id).exists()
        return is_operator, is_admin, is_teacher

    @staticmethod
    def filter_and_serialize(tasks: list[Task], user, bank: TaskBank, is_op: bool, is_adm: bool, is_tech: bool) -> list[dict]:
        visible_tasks = []
        is_moderator = is_op or is_adm

        for t in tasks:
            if is_moderator:
                visible_tasks.append(TaskVisibilityService._to_dict(t, show_answers=True))
                continue

            if is_tech:
                if t.author_id == user.id:
                    visible_tasks.append(TaskVisibilityService._to_dict(t, show_answers=True))
                    continue
                if not bank.is_open:
                    continue
                if t.status == 2 and (stable_hash(bank.id, t.id) % 100 < bank.visibility_percent):
                    visible_tasks.append(TaskVisibilityService._to_dict(t, show_answers=True))
                continue

            if not bank.is_open or t.status != 2:
                continue

            if stable_hash(bank.id, t.id) % 100 < bank.visibility_percent:
                visible_tasks.append(TaskVisibilityService._to_dict(t, show_answers=False))

        return visible_tasks

    @staticmethod
    def _to_dict(t: Task, show_answers: bool) -> dict:
        data = {
            "id": str(t.id),
            "position_id": t.position_id,
            "text": t.text,
            "image_url": t.image_url,
            "image_scale": t.image_scale,
            "image_position": t.image_position,
        }
        if show_answers:
            data["solution"] = t.solution
            data["answer"] = t.answer
            data["author_id"] = t.author_id
            data["status"] = t.status
        return data
    

try:
    CONVERT_MODELS = load_all_models()
except Exception:
    CONVERT_MODELS = None

XSLT_CHUNKS = """<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
    <xsl:template match="m:oMath">
        <xsl:text> $</xsl:text><xsl:apply-templates/><xsl:text>$ </xsl:text>
    </xsl:template>
    <xsl:template match="m:f">
        <xsl:text>\\frac{</xsl:text><xsl:apply-templates select="m:num"/><xsl:text>}{</xsl:text><xsl:apply-templates select="m:den"/><xsl:text>}</xsl:text>
    </xsl:template>
    <xsl:template match="m:sup">
        <xsl:apply-templates select="m:e"/><xsl:text>^{</xsl:text><xsl:apply-templates select="m:sup"/><xsl:text>}</xsl:text>
    </xsl:template>
    <xsl:template match="m:sub">
        <xsl:apply-templates select="m:e"/><xsl:text>_{</xsl:text><xsl:apply-templates select="m:sub"/><xsl:text>}</xsl:text>
    </xsl:template>
    <xsl:template match="m:t">
        <xsl:value-of select="."/>
    </xsl:template>
</xsl:stylesheet>"""

xslt_root = etree.XML(XSLT_CHUNKS)
transform = etree.XSLT(xslt_root)


def convert_docx_to_math_text(file_path: str) -> str:
    doc = Document(file_path)
    full_text = []

    for paragraph in doc.paragraphs:
        p_xml = paragraph._p
        if "math" in p_xml.xml:
            tree = etree.fromstring(p_xml.xml)
            result_xml = transform(tree)
            clean_text = "".join(result_xml.xpath("//text()")).strip()
            clean_text = " ".join(clean_text.split())
            if clean_text:
                full_text.append(clean_text)
        else:
            if paragraph.text.strip():
                full_text.append(paragraph.text.strip())

    return "\n\n".join(full_text)


def convert_pdf_to_math_text(file_path: str) -> str:
    if not CONVERT_MODELS:
        raise HTTPException(500, "PDF парсер не инициализирован (отсутствуют веса моделей)")
    
    full_text, _, _ = convert_single_pdf(file_path, CONVERT_MODELS)
    return full_text
# -*- coding: utf-8 -*-
"""
只產生「系統架構圖」單獨一份 Word 檔，方便直接複製貼進手改中的海報（改.docx）。
版面與海報同寬（A3 直式、左右邊界 1.2 cm），貼過去不會跑版。
輸出：
  docs/03_海報/系統架構圖.docx
"""
import os
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn

from gen_poster import build_arch_figure, body, bullet, MY_C

HERE = os.path.dirname(os.path.realpath(__file__))
OUT_NAME = os.environ.get("ARCH_OUT", "系統架構圖.docx")


def build():
    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.PORTRAIT
    sec.page_width = Cm(29.7)
    sec.page_height = Cm(42.0)
    sec.top_margin = Cm(1.1)
    sec.bottom_margin = Cm(1.1)
    sec.left_margin = Cm(1.2)
    sec.right_margin = Cm(1.2)

    style = doc.styles['Normal']
    style.font.name = "Times New Roman"
    style.font.size = Pt(10.5)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.makeelement(qn('w:rFonts'), {})
    rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), "標楷體")

    body(doc, "系統由四層協作構成：指令由上而下（左側紅色箭頭），感測資料與執行狀態由下而上"
              "（右側灰色箭頭），形成閉環。圖中紫色方塊為本專題自行開發，其餘為硬體與 ROS 現成套件。",
         after=4, size=10.5)

    build_arch_figure(doc)

    bullet(doc, "互動關鍵：", "現成套件只會「從 A 走到 B」，不會回答「怎麼走才能不重複走遍整個房間」——"
                           "那條全覆蓋路線正是 ② 層的 coverage_planner 算出來的；move_base 一次只收一個"
                           "目標，逐點排隊、監控、容錯、可中止這層調度也由 map_server 實作。低耦合設計下，"
                           "coverage_planner 完全不 import rospy，可獨立單元測試並被多個節點共用。",
           lead_color=MY_C, after=2)

    out = os.path.join(HERE, OUT_NAME)
    doc.save(out)
    return out


if __name__ == "__main__":
    print("生成完成：", build())

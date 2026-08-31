# -*- coding: utf-8 -*-
"""
以 docs/03_海報/改.docx 為底本，產生內容加深後的 改_v2.docx。

原檔的排版全部由「浮動文字方塊」構成（A3 直式 29.7×42 cm），本腳本不動版面骨架，
只做四件事：
  1. 重寫三個核心方法方塊（安全邊距膨脹、PCA 主軸對齊、牛耕式演算法）的內文；
  2. 把右下角原本只有標題「六、」的區塊補上小節名稱；
  3. 複製 PCA 方塊的 XML 結構，在右下角新建一個內文方塊放「六、驗證結果與討論」；
  4. 依新內文長度調整左上、左下兩個方塊的高度。

Word 檔內的每個文字方塊都存兩份（mc:Choice 的 DrawingML 與 mc:Fallback 的 VML），
因此所有替換都必須對兩份同時生效；本腳本以 txbxContent 為單位掃描全部出現位置。

用法：
    python gen_poster_v2.py
"""
import os
import re
import shutil
import zipfile

HERE = os.path.dirname(os.path.realpath(__file__))
SRC = os.path.join(HERE, "改.docx")
DST = os.path.join(HERE, "改_v2.docx")

EMU_PER_CM = 914400 / 2.54
PT_PER_CM = 72 / 2.54

# 內文字級（half-point）：22 = 11 pt。原檔為 12 pt，但加深後的內容塞不進既有框位，
# 故核心方法四格統一降一級；「一、研究動機」維持 12 pt，形成層級差。
SZ = 22
LINE = 240          # w:line，240 twips = 12 pt 固定行高
AFTER_GAP = 100     # 段後間距 twips = 5 pt


# ── 產生段落 XML ──────────────────────────────────────
def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run(text, bold=False):
    b = "<w:b/>" if bold else ""
    return (
        '<w:r><w:rPr><w:rFonts w:cs="Times New Roman" w:hint="eastAsia"/>'
        f'{b}<w:sz w:val="{SZ}"/><w:szCs w:val="{SZ}"/>'
        '<w:lang w:eastAsia="zh-TW"/></w:rPr>'
        f'<w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'
    )


def para(segments, after=0, indent=0):
    """segments: 字串，或 [(文字, 是否粗體), ...]。"""
    if isinstance(segments, str):
        segments = [(segments, False)]
    ind = f'<w:ind w:firstLine="{indent}"/>' if indent else ""
    body = "".join(run(t, b) for t, b in segments)
    return (
        "<w:p><w:pPr>"
        f'<w:spacing w:after="{after}" w:line="{LINE}" w:lineRule="exact"/>'
        f"{ind}"
        '<w:jc w:val="both"/>'
        f'<w:rPr><w:rFonts w:cs="Times New Roman"/><w:sz w:val="{SZ}"/>'
        f'<w:szCs w:val="{SZ}"/><w:lang w:eastAsia="zh-TW"/></w:rPr>'
        "</w:pPr>"
        f"{body}</w:p>"
    )


def _width(text):
    """以「全形字＝1」為單位估算字串寬度；半形字算 0.5。"""
    return sum(0.5 if ord(c) < 0x2000 else 1.0 for c in text)


def est_height_cm(paras, box_w_cm):
    """粗估內文佔用高度，用來檢查會不會爆框（僅供開發時參考）。"""
    inner_pt = box_w_cm * PT_PER_CM - 14.4           # 左右內距各 7.2 pt
    per_line = inner_pt / (SZ / 2)                    # 全形字寬 ≈ 字級
    line_pt = LINE / 20
    total_pt = 0.0
    for item in paras:
        seg = item[0]
        text = seg if isinstance(seg, str) else "".join(t for t, _ in seg)
        indent = (item[2] if len(item) > 2 else 0) / 20 / (SZ / 2)
        lines = max(1, -(-int(_width(text) + indent) // int(per_line)))
        total_pt += lines * line_pt + item[1] / 20
    return total_pt / PT_PER_CM + 0.25          # 文字方塊上下內距各 0.127 cm


# ── 各節新內容 ────────────────────────────────────────
P3 = [  # 三、核心方法：安全邊距膨脹（左上）
    ("安全邊距膨脹（Morphological Dilation）：把障礙物向外加厚一圈，"
     "用少量可行走面積換取路徑的安全距離。", AFTER_GAP),
    ("做法是取出占據柵格中所有障礙格，把邊距換算成格數——邊距 0.10 m、"
     "解析度 0.05 m/格，得半徑 r ＝ 2 格——再以 5×5 方形結構元素讓每個障礙格"
     "朝八方各長胖 2 格；最後把自由格扣掉這塊膨脹區，剩下的才是真正可走的區域。",
     AFTER_GAP),
    ("邊距取 0.10 m 的依據是 Burger 底盤直徑 0.20 m 的半徑，使路點落在"
     "「機器人幾何中心可安全通過」之處。方形結構元素等價於 Chebyshev 距離，"
     "對角方向多留約 41% 餘裕，偏保守，可吸收定位誤差。", AFTER_GAP),
    ("本層與 costmap inflation 分工不同：後者是執行時的即時避障，本層則在規劃"
     "階段就排除不安全位置，避免產生「規劃得出來、卻走不到」的目標點。",
     AFTER_GAP),
    ("權衡：邊距太小會貼牆、實機易觸發復原行為；太大則窄通道被整條封死、"
     "覆蓋率下降。取等於機器人半徑是兩者的折衷。", 0),
]

P4 = [  # 四、核心方法：PCA 主軸對齊（右上）
    ("主成分分析（PCA）：從一群點中找出它們最主要的散布方向。", AFTER_GAP),
    ("做法是把 N 個可走格座標減去重心得到位移 dᵢ；共變異數矩陣 C ＝ (1/N) Σ dᵢdᵢᵀ "
     "為 2×2：對角線是 x、y 方向各自的變異數，非對角線是兩方向的相關性——"
     "只要它不為零，就表示房間相對地圖是斜的。", AFTER_GAP),
    ("C 為實對稱半正定矩陣，由譜定理保證特徵值必為非負實數、兩特徵向量必定"
     "互相垂直。這正是牛耕式所需：掃描方向與換行方向天生正交，不必額外正交化。",
     AFTER_GAP),
    ("長軸（最大特徵值）當掃描方向，掃描線最少、轉彎最少；短軸（最小特徵值）"
     "當換行方向，每掃完一條平移一個間距。", AFTER_GAP),
    ("特徵向量正負號不唯一（v 與 −v 等價），會使蛇行起點左右隨機翻轉；程式固定"
     "長軸 x 分量、短軸 y 分量為正，讓同一張地圖每次都得到完全相同的路徑，"
     "便於重現與比較。", AFTER_GAP),
    ("方向來自空間本身的散布統計而非地圖座標軸，房間擺得再斜，掃描線都會"
     "自動貼齊長邊。", 0),
]

P5 = [  # 五、核心方法：牛耕式演算法（左下）
    ("牛耕路點生成（Waypoint Generation）：把投影後的一維座標，"
     "轉回世界座標的路點串列。", AFTER_GAP),
    ("做法是在投影空間中決定每條掃描線的兩個端點，再用「重心 ＋ 長軸分量 × "
     "長軸向量 ＋ 短軸分量 × 短軸向量」還原成地圖上的實際公尺座標。掃描位置從"
     "短軸投影的最小值加半個間距開始，每次累加一個間距往前推；每一輪先用遮罩"
     "取出屬於該帶的可走格，該帶內沒有任何可走格就整條跳過。", AFTER_GAP),
    ("間距取 0.18 m 的依據：覆蓋寬度約 0.20 m，相鄰掃描線刻意重疊約 10% 以吸收"
     "循跡誤差；首條掃描線內縮半個間距，使兩側邊界的覆蓋量對稱。", AFTER_GAP),
    ("三個容易忽略的細節：", 0),
    ("交替旗標：每產生一條有效線段就翻轉一次，確保是蛇行而非每條都從同一側開始。",
     0, 220),
    ("空帶跳過：遮罩沒命中任何點時不翻轉方向，避免跳過一條而讓蛇行順序錯亂。",
     0, 220),
    ("端點取投影極值：目前每條帶只取最小與最大投影值當兩端，等於假設該帶連通；"
     "此假設在凹形或帶柱子的房間會失效，是本專題的主要限制，處理見第六節。",
     0, 220),
]

P6 = [  # 六、驗證結果與討論（右下，新建方塊）
    ([("實機驗證：", True),
      ("於 TurtleBot3 Burger 上先以 SLAM 建圖並固定起點位姿，再由網頁觸發覆蓋任務。"
       "路點依序包成導航目標交給 move_base 執行，網頁每秒回報第 i／n 點進度與機器人"
       "即時位置；到不了的路點會記錄後跳過而非卡死，任務可隨時中止並取消所有目標。",
       False)], AFTER_GAP),
    ([("量化比較（同一張地圖、同一起點，僅改掃描方向）：", True)], 0),
    ("地圖軸對齊：掃描線 ___ 條、路徑長 ___ m、累積轉彎 ___°、耗時 ___ ms",
     0, 220),
    ("PCA 主軸對齊：掃描線 ___ 條、路徑長 ___ m、累積轉彎 ___°、耗時 ___ ms",
     AFTER_GAP, 220),
    ([("已知限制：", True),
      ("全域單一 PCA 取的是整片自由空間的平均主軸，對 L 型、多房間等凹形場景並非"
       "最佳；且掃描帶僅取投影極值當端點，帶被障礙物切斷時會產生跨越障礙的線段，"
       "該段由 move_base 繞行，未計入覆蓋規劃。", False)], AFTER_GAP),
    ([("未來工作：", True),
      ("(1) 依相鄰掃描帶連通段數的變化偵測臨界點，做真正的牛耕式區域分解；"
       "(2) 各子區域各自求 PCA 主軸；(3) 於區域鄰接圖上最佳化走訪順序；"
       "(4) 統計「實際走過格／應覆蓋格」的線上覆蓋率。", False)], 0),
]


# 四個方塊：(標題, 內容, 框寬 cm, 框高上限 cm)
# 上限來自版面實測：上排可用 23.35→30.60、下排可用 32.15→40.70（頁高 42、下邊界 1.27）
BOXES = (
    ("三 安全邊距膨脹", P3, 12.70, 7.10),
    ("四 PCA 主軸對齊", P4, 13.11, 7.25),
    ("五 牛耕式演算法", P5, 12.70, 8.50),
    ("六 驗證結果與討論", P6, 13.11, 8.50),
)


def build(paras):
    out = []
    for item in paras:
        seg, after = item[0], item[1]
        indent = item[2] if len(item) > 2 else 0
        out.append(para(seg, after=after, indent=indent))
    return "".join(out)


def check(paras, label, w_cm, limit_cm):
    h = est_height_cm(paras, w_cm)
    flag = "OK  " if h <= limit_cm else "爆框"
    print(f"  [{flag}] {label}：約 {h:.2f} cm / 上限 {limit_cm:.2f} cm")
    return h


# ── XML 操作工具 ──────────────────────────────────────
def txbx_blocks(xml):
    """回傳所有 txbxContent 的 (內層起, 內層迄, 內層純文字)。"""
    res = []
    for m in re.finditer(r"<w:txbxContent>(.*?)</w:txbxContent>", xml, re.S):
        txt = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", m.group(1), re.S))
        res.append((m.start(1), m.end(1), re.sub(r"<[^>]+>", "", txt)))
    return res


def replace_txbx(xml, signature, new_inner):
    """把所有內文以 signature 開頭的文字方塊，換成 new_inner。"""
    hits = [b for b in txbx_blocks(xml) if b[2].startswith(signature)]
    if not hits:
        raise SystemExit(f"找不到文字方塊：{signature!r}")
    for s, e, _ in reversed(hits):          # 由後往前改，位移才不會亂掉
        xml = xml[:s] + new_inner + xml[e:]
    return xml, len(hits)


def alt_span(xml, signature):
    """找出內文以 signature 開頭的文字方塊，其外層 mc:AlternateContent 範圍。"""
    hits = [b for b in txbx_blocks(xml) if b[2].startswith(signature)]
    if not hits:
        raise SystemExit(f"找不到文字方塊：{signature!r}")
    pos = hits[0][0]
    s = xml.rfind("<mc:AlternateContent>", 0, pos)
    e = xml.find("</mc:AlternateContent>", pos) + len("</mc:AlternateContent>")
    return s, e


def set_box_size(xml, signature, w_cm=None, h_cm=None):
    """調整某文字方塊的寬高（DrawingML 與 VML 兩份同步）。"""
    s, e = alt_span(xml, signature)
    seg = xml[s:e]
    cx, cy = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"/>', seg).groups()
    ncx = str(int(round(w_cm * EMU_PER_CM))) if w_cm else cx
    ncy = str(int(round(h_cm * EMU_PER_CM))) if h_cm else cy
    seg = seg.replace(f'cx="{cx}" cy="{cy}"', f'cx="{ncx}" cy="{ncy}"')
    if w_cm:
        seg = re.sub(r"width:[\d.]+pt", "width:%.2fpt" % (w_cm * PT_PER_CM), seg)
    if h_cm:
        seg = re.sub(r"height:[\d.]+pt", "height:%.2fpt" % (h_cm * PT_PER_CM), seg)
    return xml[:s] + seg + xml[e:]


def clone_box(xml, signature, y_cm, h_cm, new_inner):
    """複製某文字方塊的完整 XML 結構，改位置/大小/內容後回傳新片段。"""
    s, e = alt_span(xml, signature)
    seg = xml[s:e]

    cx, cy = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"/>', seg).groups()
    seg = seg.replace(f'cx="{cx}" cy="{cy}"',
                      f'cx="{cx}" cy="{int(round(h_cm * EMU_PER_CM))}"')
    seg = re.sub(r"height:[\d.]+pt", "height:%.2fpt" % (h_cm * PT_PER_CM), seg)

    # 垂直位置：DrawingML 用 EMU、VML 用 pt
    seg = re.sub(r"(<wp:positionV relativeFrom=\"paragraph\">\s*<wp:posOffset>)-?\d+",
                 lambda m: m.group(1) + str(int(round(y_cm * EMU_PER_CM))), seg)
    seg = re.sub(r"margin-top:[\d.]+pt", "margin-top:%.2fpt" % (y_cm * PT_PER_CM), seg)

    # 讓識別碼唯一，避免 Word 判定為重複物件
    seg = re.sub(r'<wp:docPr id="\d+" name="[^"]*"/>',
                 '<wp:docPr id="1846164999" name="文字方塊 99"/>', seg)
    seg = re.sub(r'id="_x0000_s\d+"', 'id="_x0000_s1099"', seg)
    seg = seg.replace('relativeHeight="251672576"', 'relativeHeight="251699712"')
    seg = seg.replace("z-index:251672576", "z-index:251699712")
    seg = re.sub(r'(wp14:anchorId|w14:anchorId)="[0-9A-Fa-f]{8}"',
                 lambda m: m.group(1) + '="5383F999"', seg)
    seg = re.sub(r'wp14:editId="[0-9A-Fa-f]{8}"', 'wp14:editId="08B9D999"', seg)

    # 換掉兩份 txbxContent 的內容
    for m in reversed(list(re.finditer(r"<w:txbxContent>(.*?)</w:txbxContent>",
                                       seg, re.S))):
        seg = seg[:m.start(1)] + new_inner + seg[m.end(1):]
    return seg


# ── 主流程 ────────────────────────────────────────────
def main():
    if not os.path.exists(SRC):
        raise SystemExit(f"找不到來源檔：{SRC}")
    shutil.copyfile(SRC, DST)

    with zipfile.ZipFile(SRC) as z:
        parts = {i.filename: z.read(i.filename) for i in z.infolist()}
        order = [i.filename for i in z.infolist()]
    xml = parts["word/document.xml"].decode("utf-8")

    # 1) 重寫三個核心方法方塊
    for sig, paras, label in (
        ("安全邊距膨脹（Morphological Dilation）", P3, "三 安全邊距膨脹"),
        ("主成分分析（PCA）", P4, "四 PCA 主軸對齊"),
        ("牛耕路點生成（Waypoint Generation）", P5, "五 牛耕式演算法"),
    ):
        xml, n = replace_txbx(xml, sig, build(paras))
        print(f"  重寫 {label}（{n} 份）")

    # 2) 右下角標題補上小節名稱
    n = xml.count("<w:t>六、</w:t>")
    xml = xml.replace("<w:t>六、</w:t>", "<w:t>六、驗證結果與討論</w:t>")
    print(f"  標題補字：六、→ 六、驗證結果與討論（{n} 份）")

    # 3) 調整左上／左下方塊高度，容納加長後的內文
    xml = set_box_size(xml, "安全邊距膨脹（Morphological Dilation）", h_cm=7.10)
    xml = set_box_size(xml, "牛耕路點生成（Waypoint Generation）", h_cm=8.50)
    print("  調整方塊高度：三 → 7.10 cm、五 → 8.50 cm")

    # 4) 以 PCA 方塊為模板，於右下角新建「六」的內文方塊
    new_box = clone_box(xml, "主成分分析（PCA）", y_cm=32.15, h_cm=8.50,
                        new_inner=build(P6))
    s, e = alt_span(xml, "主成分分析（PCA）")
    xml = xml[:e] + new_box + xml[e:]
    print("  新建方塊：六、驗證結果與討論（右下，13.11 × 8.50 cm）")

    parts["word/document.xml"] = xml.encode("utf-8")
    with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as z:
        for name in order:
            z.writestr(name, parts[name])

    print(f"\n輸出：{DST}")
    print("\n各節內文高度粗估（框高上限）：")
    for label, paras, w, limit in BOXES:
        check(paras, label, w, limit)


if __name__ == "__main__":
    main()

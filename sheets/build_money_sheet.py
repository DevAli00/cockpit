"""Builds an empty 'Money Cockpit' workbook that mirrors the Cockpit app's Money module."""
from __future__ import annotations

import sys
from datetime import date

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule, DataBarRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

OUT = sys.argv[1]

# ---- capacities -------------------------------------------------------------------------------
TX0, TX1 = 5, 2004      # Transactions rows
RC0, RC1 = 5, 104       # Recurring rows
FD0, FD1 = 5, 24        # Funds rows (20 funds)
MV0, MV1 = 5, 1004      # Fund moves rows
AC0, AC1 = 5, 34        # Accounts rows (30 accounts)
BL0, BL1 = 5, 3004      # Balances rows
MO0, MO1 = 6, 65        # Months rows (60 months)
CT0, CT1 = 10, 40       # Settings list rows

# ---- styles -----------------------------------------------------------------------------------
ARIAL = "Arial"
F_BASE = Font(name=ARIAL, size=10)
F_INPUT = Font(name=ARIAL, size=10, color="0000FF")
F_LINK = Font(name=ARIAL, size=10, color="008000")
F_HEAD = Font(name=ARIAL, size=10, bold=True, color="FFFFFF")
F_TITLE = Font(name=ARIAL, size=16, bold=True, color="1F3864")
F_SUB = Font(name=ARIAL, size=10, italic=True, color="595959")
F_H2 = Font(name=ARIAL, size=12, bold=True, color="1F3864")
F_BOLD = Font(name=ARIAL, size=10, bold=True)
F_KPI = Font(name=ARIAL, size=14, bold=True, color="1F3864")
FILL_INPUT = PatternFill("solid", fgColor="FFF2CC")
FILL_HEAD = PatternFill("solid", fgColor="1F3864")
FILL_CALC_HEAD = PatternFill("solid", fgColor="2E75B6")
FILL_KPI = PatternFill("solid", fgColor="EAF1FB")
FILL_EX = PatternFill("solid", fgColor="F2F2F2")
THIN = Side(style="thin", color="D9D9D9")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
MONEY = '#,##0.00;[Red]-#,##0.00;"-"'
MONEY0 = '#,##0;[Red]-#,##0;"-"'
PCT = '0%;[Red]-0%;"-"'
DATE = "dd/mm/yyyy"
MONTH = "mmm yyyy"
HIDE_ZERO = '0;-0;;@'

wb = Workbook()
wb._named_styles["Normal"].font = Font(name=ARIAL, size=10)


def sheet(title: str, tab: str | None = None):
    ws = wb.create_sheet(title)
    if tab:
        ws.sheet_properties.tabColor = tab
    ws.sheet_view.showGridLines = False
    return ws


def title(ws, text: str, sub: str) -> None:
    ws["A1"] = text
    ws["A1"].font = F_TITLE
    ws["A2"] = sub
    ws["A2"].font = F_SUB


def headers(ws, row: int, cols: list[tuple[str, int, bool]]) -> None:
    """cols: (header, width, is_input)."""
    for i, (h, w, inp) in enumerate(cols, start=1):
        c = ws.cell(row=row, column=i, value=h)
        c.font = F_HEAD
        c.fill = FILL_HEAD if inp else FILL_CALC_HEAD
        c.alignment = CENTER
        c.border = BOX
        ws.column_dimensions[L(i)].width = w
    ws.row_dimensions[row].height = 32
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def input_block(ws, r0: int, r1: int, cols: list[int], fmt: dict[int, str] | None = None) -> None:
    fmt = fmt or {}
    for r in range(r0, r1 + 1):
        for c in cols:
            cell = ws.cell(row=r, column=c)
            cell.fill = FILL_INPUT
            cell.font = F_INPUT
            cell.border = BOX
            if c in fmt:
                cell.number_format = fmt[c]


def formula_col(ws, col: int, r0: int, r1: int, template: str, fmt: str | None = None, font=F_BASE) -> None:
    for r in range(r0, r1 + 1):
        cell = ws.cell(row=r, column=col, value=template.replace("{r}", str(r)))
        cell.font = font
        cell.border = BOX
        if fmt:
            cell.number_format = fmt


def name(n: str, ref: str) -> None:
    wb.defined_names[n] = DefinedName(n, attr_text=ref)


def rng(sheet_name: str, col: str, r0: int, r1: int) -> str:
    q = f"'{sheet_name}'" if " " in sheet_name else sheet_name
    return f"{q}!${col}${r0}:${col}${r1}"


# Range shortcuts used in formulas -------------------------------------------------------------
T = {c: rng("Transactions", c, TX0, TX1) for c in "ABCDEFG"}
R = {c: rng("Recurring", c, RC0, RC1) for c in "ABCDEFGHIJK"}
FD = {c: rng("Funds", c, FD0, FD1) for c in "ABCDEFGHTU"}
MV = {c: rng("Fund moves", c, MV0, MV1) for c in "ABC"}
BL = {c: rng("Balances", c, BL0, BL1) for c in "ABC"}
MO = {c: rng("Months", c, MO0, MO1) for c in "ABCDEFGHIJKLMNOPQRSTU"}

# ===============================================================================================
# How to use (filled at the end, but created first so it is the first tab)
guide = wb.active
guide.title = "How to use"
guide.sheet_properties.tabColor = "1F3864"
guide.sheet_view.showGridLines = False
dash = sheet("Dashboard", "1F3864")
tx = sheet("Transactions", "FFC000")
rc = sheet("Recurring", "FFC000")
fd = sheet("Funds", "FFC000")
mv = sheet("Fund moves", "FFC000")
ac = sheet("Accounts", "FFC000")
bl = sheet("Balances", "FFC000")
st = sheet("Settings", "FFC000")
mo = sheet("Months", "A6A6A6")
nw = sheet("NW grid", "A6A6A6")

# ===============================================================================================
# Settings
title(st, "SETTINGS", "Fill once. Yellow cells are yours to edit; lists feed the drop-downs in the other tabs.")
for r, (label, val, fmt, note) in enumerate([
    ("Your name", None, None, "Shown on the Dashboard."),
    ("Currency symbol", "€", None, "Shown in headers (amounts are plain numbers)."),
    ("First month of this sheet", date(2026, 1, 1), MONTH,
     "The 'Months' engine covers 60 months from here. Set it to the first month you will log."),
], start=4):
    st.cell(row=r, column=2, value=label).font = F_BOLD
    c = st.cell(row=r, column=3, value=val)
    c.fill, c.font, c.border = FILL_INPUT, F_INPUT, BOX
    if fmt:
        c.number_format = fmt
    st.cell(row=r, column=4, value=note).font = F_SUB
st.column_dimensions["A"].width = 2
st.column_dimensions["B"].width = 26
st.column_dimensions["C"].width = 16
st.column_dimensions["D"].width = 4

LISTS = {
    "E": ("Income categories", ["Salary", "Freelance", "Bonus", "Refunds", "Gifts", "Investment income", "Other income"]),
    "F": ("Expense categories", ["Housing", "Groceries", "Transport", "Utilities & phone", "Health", "Subscriptions",
                                 "Eating out", "Shopping", "Travel", "Sport", "Education & books", "Family",
                                 "Charity & zakat", "Gifts", "Other expense"]),
    "G": ("Fund kinds", ["Travel", "Emergency", "Hajj / Umrah", "Car", "Home", "Education", "Gifts & Eid",
                         "Charity & zakat", "Big purchase", "Wedding", "Other"]),
    "H": ("Account types", ["Current account / cash", "Savings", "Investments", "Retirement", "Crypto", "Property",
                            "Vehicle", "Other asset", "Loan", "Mortgage", "Credit card", "Other debt"]),
}
ASSET_OR_DEBT = ["Asset"] * 8 + ["Debt"] * 4
for col, (head, items) in LISTS.items():
    h = st[f"{col}{CT0 - 1}"]
    h.value, h.font, h.fill, h.alignment = head, F_HEAD, FILL_HEAD, CENTER
    st.column_dimensions[col].width = 24
    for i in range(CT1 - CT0 + 1):
        c = st[f"{col}{CT0 + i}"]
        c.fill, c.font, c.border = FILL_INPUT, F_INPUT, BOX
        if i < len(items):
            c.value = items[i]
h = st[f"I{CT0 - 1}"]
h.value, h.font, h.fill, h.alignment = "Asset or debt", F_HEAD, FILL_HEAD, CENTER
st.column_dimensions["I"].width = 14
for i in range(CT1 - CT0 + 1):
    c = st[f"I{CT0 + i}"]
    c.fill, c.font, c.border = FILL_INPUT, F_INPUT, BOX
    if i < len(ASSET_OR_DEBT):
        c.value = ASSET_OR_DEBT[i]
st[f"E{CT0 - 2}"] = "Add your own at the bottom of any list; keep names unique."
st[f"E{CT0 - 2}"].font = F_SUB

name("cat_Income", rng("Settings", "E", CT0, CT1))
name("cat_Expense", rng("Settings", "F", CT0, CT1))
name("FundKinds", rng("Settings", "G", CT0, CT1))
name("AccountTypes", rng("Settings", "H", CT0, CT1))
name("FundNames", rng("Funds", "A", FD0, FD1))
name("AccountNames", rng("Accounts", "A", AC0, AC1))
CUR = "Settings!$C$5"
FIRST_MONTH = "Settings!$C$6"


def dv_list(ws, formula: str, ref: str, msg: str | None = None, allow_blank: bool = True) -> None:
    dv = DataValidation(type="list", formula1=formula, allow_blank=allow_blank, showErrorMessage=True)
    if msg:
        dv.error, dv.errorTitle = msg, "Pick from the list"
    ws.add_data_validation(dv)
    dv.add(ref)


def dv_number(ws, ref: str, op: str, v1: str, v2: str | None = None, msg: str = "Invalid number") -> None:
    dv = DataValidation(type="decimal", operator=op, formula1=v1, formula2=v2, allow_blank=True,
                        showErrorMessage=True, error=msg, errorTitle="Check this value")
    ws.add_data_validation(dv)
    dv.add(ref)


def dv_date(ws, ref: str) -> None:
    dv = DataValidation(type="date", operator="greaterThan", formula1="1", allow_blank=True,
                        showErrorMessage=True, error="Type a date, e.g. 05/11/2026", errorTitle="Date")
    ws.add_data_validation(dv)
    dv.add(ref)


# ===============================================================================================
# Transactions
title(tx, "TRANSACTIONS", "One line per income or expense. Optional 'Fund': an expense PAID FROM a fund, "
      "or an income that goes INTO a fund. Dates in the future are ignored until they happen.")
headers(tx, 4, [("Date", 12, True), ("Type", 10, True), ("Category", 20, True), ("Label", 30, True),
                ("Amount", 13, True), ("Fund (optional)", 20, True), ("Notes", 30, True)])
tx["E4"] = f'="Amount ("&{CUR}&")"'
input_block(tx, TX0, TX1, [1, 2, 3, 4, 5, 6, 7], {1: DATE, 5: MONEY})
dv_date(tx, f"A{TX0}:A{TX1}")
dv_list(tx, '"Income,Expense"', f"B{TX0}:B{TX1}", "Type must be Income or Expense")
dv_list(tx, 'INDIRECT("cat_"&$B5)', f"C{TX0}:C{TX1}", "Pick a category (choose the Type first)")
dv_number(tx, f"E{TX0}:E{TX1}", "greaterThan", "0", msg="Amounts are positive; the Type says if it is in or out")
dv_list(tx, "=FundNames", f"F{TX0}:F{TX1}", "Pick one of your funds (Funds tab) or leave empty")

# ===============================================================================================
# Recurring
title(rc, "RECURRING", "Salary, rent, subscriptions… entered once, counted automatically on each billing day "
      "from Start to End (or today). Billing day = the Start day (29-31 become the 28th).")
headers(rc, 4, [("Label", 26, True), ("Type", 10, True), ("Category", 20, True), ("Amount", 13, True),
                ("Every", 11, True), ("Start", 12, True), ("End (optional)", 13, True), ("Fund (optional)", 20, True),
                ("Billing day", 10, False), ("Times billed so far", 12, False), ("Total so far", 14, False),
                ("Status", 14, False)])
rc["D4"] = f'="Amount ("&{CUR}&")"'
rc["K4"] = f'="Total so far ("&{CUR}&")"'
input_block(rc, RC0, RC1, [1, 2, 3, 4, 5, 6, 7, 8], {4: MONEY, 6: DATE, 7: DATE})
dv_list(rc, '"Income,Expense"', f"B{RC0}:B{RC1}", "Type must be Income or Expense")
dv_list(rc, 'INDIRECT("cat_"&$B5)', f"C{RC0}:C{RC1}", "Pick a category (choose the Type first)")
dv_number(rc, f"D{RC0}:D{RC1}", "greaterThan", "0", msg="Amounts are positive")
dv_list(rc, '"Monthly,Yearly"', f"E{RC0}:E{RC1}", "Monthly or Yearly")
dv_date(rc, f"F{RC0}:G{RC1}")
dv_list(rc, "=FundNames", f"H{RC0}:H{RC1}", "Pick one of your funds or leave empty")
LAST = "MIN(IF($G{r}=\"\",TODAY(),$G{r}),TODAY())"
formula_col(rc, 9, RC0, RC1, '=IF($F{r}="",0,MIN(DAY($F{r}),28))', HIDE_ZERO)
formula_col(rc, 10, RC0, RC1,
            '=IF(OR($F{r}="",$D{r}=""),0,MAX(0,IF($E{r}="Yearly",'
            f'YEAR({LAST})-YEAR($F{{r}})+1-(DATE(YEAR($F{{r}}),MONTH($F{{r}}),$I{{r}})<$F{{r}})'
            f'-(DATE(YEAR({LAST}),MONTH($F{{r}}),$I{{r}})>{LAST}),'
            f'(YEAR({LAST})-YEAR($F{{r}}))*12+MONTH({LAST})-MONTH($F{{r}})+1-($I{{r}}<DAY($F{{r}}))-(DAY({LAST})<$I{{r}}))))',
            HIDE_ZERO)
formula_col(rc, 11, RC0, RC1, '=$J{r}*N($D{r})', MONEY)
formula_col(rc, 12, RC0, RC1,
            '=IF($A{r}="","",IF($F{r}>TODAY(),"Not started",IF(AND($G{r}<>"",$G{r}<=TODAY()),"Stopped","Running")))')

# ===============================================================================================
# Funds
title(fd, "FUNDS", "Savings pots (travel, emergency, Hajj, gifts…). They fill themselves with the automation "
      "you set, plus moves by hand (Fund moves tab), plus transactions linked to them.")
headers(fd, 4, [("Fund name", 22, True), ("Kind", 16, True), ("Target", 12, True), ("Deadline (optional)", 12, True),
                ("Put in every month", 12, True), ("On day (1-28)", 9, True), ("% of every income", 10, True),
                ("Automation starts", 12, True),
                ("Automatic monthly so far", 13, False), ("Share of income so far", 13, False),
                ("By hand (in − out)", 13, False), ("Income into fund", 12, False), ("Paid from fund", 12, False),
                ("Balance", 13, False), ("Progress", 10, False), ("Remaining", 12, False),
                ("Needed / month", 12, False), ("Needed / week", 12, False), ("Status", 18, False),
                ("(day used)", 6, False), ("(start month)", 6, False)])
input_block(fd, FD0, FD1, list(range(1, 9)), {3: MONEY, 4: DATE, 5: MONEY, 7: "0.0%", 8: DATE})
dv_list(fd, "=FundKinds", f"B{FD0}:B{FD1}", "Pick a kind (Settings tab)")
dv_number(fd, f"C{FD0}:C{FD1}", "greaterThan", "0", msg="Target must be above 0")
dv_date(fd, f"D{FD0}:D{FD1}")
dv_number(fd, f"E{FD0}:E{FD1}", "greaterThanOrEqual", "0", msg="Monthly amount cannot be negative")
dv = DataValidation(type="whole", operator="between", formula1="1", formula2="28", allow_blank=True,
                    showErrorMessage=True, error="Day 1 to 28 so it happens every month", errorTitle="Day")
fd.add_data_validation(dv); dv.add(f"F{FD0}:F{FD1}")
dv_number(fd, f"G{FD0}:G{FD1}", "between", "0", "1", msg="Between 0% and 100%")
dv_date(fd, f"H{FD0}:H{FD1}")
DD = "$T{r}"
formula_col(fd, 20, FD0, FD1, '=IF($F{r}="",1,$F{r})', HIDE_ZERO)                         # T day used
formula_col(fd, 21, FD0, FD1, '=IF($H{r}="",0,DATE(YEAR($H{r}),MONTH($H{r}),1))', HIDE_ZERO)  # U start month
formula_col(fd, 9, FD0, FD1,
            '=IF(OR($A{r}="",$H{r}="",N($E{r})=0),0,$E{r}*MAX(0,(YEAR(TODAY())-YEAR($H{r}))*12+MONTH(TODAY())'
            f'-MONTH($H{{r}})+1-(DAY($H{{r}})>{DD})-(DAY(TODAY())<{DD})))', MONEY)
formula_col(fd, 10, FD0, FD1,
            f'=IF(OR($A{{r}}="",$H{{r}}="",N($G{{r}})=0),0,ROUNDDOWN($G{{r}}*SUMPRODUCT(({MO["A"]}>=$U{{r}})*{MO["I"]}),2))',
            MONEY)
formula_col(fd, 11, FD0, FD1,
            f'=IF($A{{r}}="",0,SUMIFS({MV["C"]},{MV["B"]},$A{{r}},{MV["A"]},"<="&TODAY()))', MONEY)
formula_col(fd, 12, FD0, FD1,
            f'=IF($A{{r}}="",0,SUMIFS({T["E"]},{T["F"]},$A{{r}},{T["B"]},"Income",{T["A"]},"<="&TODAY())'
            f'+SUMIFS({R["K"]},{R["H"]},$A{{r}},{R["B"]},"Income"))', MONEY)
formula_col(fd, 13, FD0, FD1,
            f'=IF($A{{r}}="",0,SUMIFS({T["E"]},{T["F"]},$A{{r}},{T["B"]},"Expense",{T["A"]},"<="&TODAY())'
            f'+SUMIFS({R["K"]},{R["H"]},$A{{r}},{R["B"]},"Expense"))', MONEY)
formula_col(fd, 14, FD0, FD1, '=IF($A{r}="","",$I{r}+$J{r}+$K{r}+$L{r}-$M{r})', MONEY, F_BOLD)
formula_col(fd, 15, FD0, FD1, '=IF(OR($A{r}="",N($C{r})=0),"",MAX(0,MIN(1,$N{r}/$C{r})))', PCT)
formula_col(fd, 16, FD0, FD1, '=IF($A{r}="","",MAX(0,N($C{r})-$N{r}))', MONEY)
formula_col(fd, 17, FD0, FD1,
            '=IF(OR($A{r}="",$D{r}=""),"",IF($P{r}=0,0,ROUNDUP($P{r}/MAX(1,(YEAR($D{r})-YEAR(TODAY()))*12'
            '+MONTH($D{r})-MONTH(TODAY())+1),2)))', MONEY)
formula_col(fd, 18, FD0, FD1,
            '=IF(OR($A{r}="",$D{r}=""),"",IF($P{r}=0,0,ROUNDUP($P{r}/MAX(1,ROUNDUP(($D{r}-TODAY())/7,0)),2)))', MONEY)
formula_col(fd, 19, FD0, FD1,
            '=IF($A{r}="","",IF($N{r}<0,"Overspent",IF($N{r}>=N($C{r}),"Funded",'
            'IF(AND(OR(N($E{r})>0,N($G{r})>0),$H{r}=""),"Set Automation starts",'
            'IF(AND($D{r}<>"",N($E{r})<N($Q{r})),"Behind schedule","On its way")))))')
for c in ("T", "U"):
    fd.column_dimensions[c].hidden = True
tr = FD1 + 2
fd[f"A{tr}"] = "TOTAL"
fd[f"A{tr}"].font = F_BOLD
for col in "CNPQ":
    fd[f"{col}{tr}"] = f"=SUM({col}{FD0}:{col}{FD1})"
    fd[f"{col}{tr}"].font = F_BOLD
    fd[f"{col}{tr}"].number_format = MONEY
fd[f"G{tr}"] = f"=SUM(G{FD0}:G{FD1})"
fd[f"G{tr}"].number_format = "0.0%"
fd[f"G{tr}"].font = F_BOLD
fd[f"H{tr}"] = f'=IF(G{tr}>1,"⚠ Over 100% of income!","")'
fd[f"H{tr}"].font = Font(name=ARIAL, size=10, bold=True, color="C00000")
fd.conditional_formatting.add(f"O{FD0}:O{FD1}", DataBarRule(start_type="num", start_value=0, end_type="num",
                                                            end_value=1, color="5B9BD5"))
for text, color in (("Overspent", "C00000"), ("Behind", "C55A11"), ("Funded", "00804A"), ("Set Automation", "C55A11")):
    fd.conditional_formatting.add(
        f"S{FD0}:S{FD1}",
        FormulaRule(formula=[f'ISNUMBER(SEARCH("{text}",$S{FD0}))'], font=Font(name=ARIAL, bold=True, color=color)))

# ===============================================================================================
# Fund moves
title(mv, "FUND MOVES", "Money you put in or take out by hand. Positive = put in, negative = take out.")
headers(mv, 4, [("Date", 12, True), ("Fund", 22, True), ("Amount (+ in / − out)", 16, True), ("Note", 36, True)])
input_block(mv, MV0, MV1, [1, 2, 3, 4], {1: DATE, 3: MONEY})
dv_date(mv, f"A{MV0}:A{MV1}")
dv_list(mv, "=FundNames", f"B{MV0}:B{MV1}", "Pick one of your funds")

# ===============================================================================================
# Accounts
title(ac, "ACCOUNTS", "Everything you own and owe. Balances go in the Balances tab; the latest one counts.")
headers(ac, 4, [("Account name", 24, True), ("Type", 22, True), ("Asset or debt", 11, False), ("Bank / where", 18, True),
                ("Latest balance date", 12, False), ("Latest balance", 14, False), ("Counts as", 14, False),
                ("Balance date 30 days ago", 12, False), ("Counts as 30 days ago", 14, False),
                ("Days since update", 10, False), ("Needs update?", 12, False)])
input_block(ac, AC0, AC1, [1, 2, 4])
dv_list(ac, "=AccountTypes", f"B{AC0}:B{AC1}", "Pick a type (Settings tab)")
ST_H, ST_I = rng("Settings", "H", CT0, CT1), rng("Settings", "I", CT0, CT1)
formula_col(ac, 3, AC0, AC1, f'=IF($A{{r}}="","",IFERROR(INDEX({ST_I},MATCH($B{{r}},{ST_H},0)),"Asset"))')
formula_col(ac, 5, AC0, AC1,
            f'=IF($A{{r}}="",0,_xlfn.MAXIFS({BL["A"]},{BL["B"]},$A{{r}},{BL["A"]},"<="&TODAY()))', 'dd/mm/yyyy;;;')
formula_col(ac, 6, AC0, AC1,
            f'=IF(OR($A{{r}}="",$E{{r}}=0),0,SUMIFS({BL["C"]},{BL["B"]},$A{{r}},{BL["A"]},$E{{r}}))', MONEY)
formula_col(ac, 7, AC0, AC1, '=IF($C{r}="Debt",-$F{r},$F{r})', MONEY)
formula_col(ac, 8, AC0, AC1,
            f'=IF($A{{r}}="",0,_xlfn.MAXIFS({BL["A"]},{BL["B"]},$A{{r}},{BL["A"]},"<="&(TODAY()-30)))', 'dd/mm/yyyy;;;')
formula_col(ac, 9, AC0, AC1,
            f'=IF(OR($A{{r}}="",$H{{r}}=0),0,IF($C{{r}}="Debt",-1,1)*SUMIFS({BL["C"]},{BL["B"]},$A{{r}},{BL["A"]},$H{{r}}))',
            MONEY)
formula_col(ac, 10, AC0, AC1, '=IF($A{r}="","",IF($E{r}=0,"never",TODAY()-$E{r}))', HIDE_ZERO)
formula_col(ac, 11, AC0, AC1, '=IF($A{r}="","",IF(OR($E{r}=0,TODAY()-$E{r}>45),"Update me",""))')
ac.conditional_formatting.add(f"K{AC0}:K{AC1}", CellIsRule(operator="equal", formula=['"Update me"'],
                                                           font=Font(name=ARIAL, bold=True, color="C55A11")))

# ===============================================================================================
# Balances
title(bl, "BALANCES", "Once a month (or whenever): one line per account with today's balance. "
      "For debts, type what you still owe (a positive number).")
headers(bl, 4, [("Date", 12, True), ("Account", 26, True), ("Balance / amount owed", 18, True), ("Note", 30, True)])
input_block(bl, BL0, BL1, [1, 2, 3, 4], {1: DATE, 3: MONEY})
dv_date(bl, f"A{BL0}:A{BL1}")
dv_list(bl, "=AccountNames", f"B{BL0}:B{BL1}", "Pick one of your accounts (Accounts tab)")

# ===============================================================================================
# Months (engine)
title(mo, "MONTHS — engine (do not edit)", "Month by month totals that feed the Dashboard and the funds. "
      "Only past days count: future-dated entries wait for their date.")
mcols = [("Month", 11), ("Month end", 11), ("Income (lines)", 12), ("Income (recurring)", 12), ("Expenses (lines)", 12),
         ("Expenses (recurring)", 12), ("Income", 12), ("Expenses", 12), ("Income not routed to a fund", 13),
         ("Automatic monthly", 12), ("Share of income", 12), ("By hand in", 11), ("By hand out", 11),
         ("Income into funds", 12), ("Expenses paid from funds", 12), ("Into funds", 12), ("From funds", 12),
         ("Saved", 12), ("Savings rate", 10), ("Left over to spend", 13), ("Net worth (month end)", 14)]
for i, (h, w) in enumerate(mcols, start=1):
    c = mo.cell(row=5, column=i, value=h)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_CALC_HEAD, CENTER, BOX
    mo.column_dimensions[L(i)].width = w
mo.row_dimensions[5].height = 42
mo.freeze_panes = "B6"

UPTO = "MIN($B{r},TODAY())"


def tx_sum(type_: str, fund: str | None) -> str:
    extra = "" if fund is None else f',{T["F"]},"{fund}"'
    return (f'SUMIFS({T["E"]},{T["B"]},"{type_}",{T["A"]},">="&$A{{r}},{T["A"]},"<="&{UPTO}{extra})')


BILL = f'($A{{r}}+{R["I"]}-1)'
RC_COND = (f'({R["F"]}>0)*({R["F"]}<={BILL})*((({R["G"]}="")+({R["G"]}>={BILL}))>0)*({BILL}<=TODAY())'
           f'*((({R["E"]}<>"Yearly")+(MONTH({R["F"]})=MONTH($A{{r}})))>0)')


def rc_sum(type_: str, fund: str | None) -> str:
    f = "" if fund is None else (f'*({R["H"]}="")' if fund == "" else f'*({R["H"]}<>"")')
    return f'SUMPRODUCT({R["D"]}*({R["B"]}="{type_}")*{RC_COND}{f})'


formula_col(mo, 1, MO0, MO0, f"={FIRST_MONTH}", MONTH)
formula_col(mo, 1, MO0 + 1, MO1, "=EDATE($A{rp},1)", MONTH)
for r in range(MO0 + 1, MO1 + 1):
    mo.cell(row=r, column=1).value = f"=EDATE($A{r - 1},1)"
formula_col(mo, 2, MO0, MO1, "=EOMONTH($A{r},0)", DATE)
formula_col(mo, 3, MO0, MO1, "=" + tx_sum("Income", None), MONEY)
formula_col(mo, 4, MO0, MO1, "=" + rc_sum("Income", None), MONEY)
formula_col(mo, 5, MO0, MO1, "=" + tx_sum("Expense", None), MONEY)
formula_col(mo, 6, MO0, MO1, "=" + rc_sum("Expense", None), MONEY)
formula_col(mo, 7, MO0, MO1, "=$C{r}+$D{r}", MONEY)
formula_col(mo, 8, MO0, MO1, "=$E{r}+$F{r}", MONEY)
formula_col(mo, 9, MO0, MO1, "=" + tx_sum("Income", "") + "+" + rc_sum("Income", ""), MONEY)
formula_col(mo, 10, MO0, MO1,
            f'=SUMPRODUCT({FD["E"]}*({FD["A"]}<>"")*({FD["H"]}>0)*(($A{{r}}+{FD["T"]}-1)>={FD["H"]})'
            f'*(($A{{r}}+{FD["T"]}-1)<=TODAY()))', MONEY)
formula_col(mo, 11, MO0, MO1,
            f'=ROUNDDOWN($I{{r}}*SUMPRODUCT({FD["G"]}*({FD["A"]}<>"")*({FD["U"]}>0)*({FD["U"]}<=$A{{r}})),2)', MONEY)
formula_col(mo, 12, MO0, MO1,
            f'=SUMIFS({MV["C"]},{MV["C"]},">0",{MV["A"]},">="&$A{{r}},{MV["A"]},"<="&{UPTO})', MONEY)
formula_col(mo, 13, MO0, MO1,
            f'=-SUMIFS({MV["C"]},{MV["C"]},"<0",{MV["A"]},">="&$A{{r}},{MV["A"]},"<="&{UPTO})', MONEY)
formula_col(mo, 14, MO0, MO1, "=" + tx_sum("Income", "<>") + "+" + rc_sum("Income", "<>"), MONEY)
formula_col(mo, 15, MO0, MO1, "=" + tx_sum("Expense", "<>") + "+" + rc_sum("Expense", "<>"), MONEY)
formula_col(mo, 16, MO0, MO1, "=$J{r}+$K{r}+$L{r}+$N{r}", MONEY)
formula_col(mo, 17, MO0, MO1, "=$M{r}+$O{r}", MONEY)
formula_col(mo, 18, MO0, MO1, "=$G{r}-$H{r}", MONEY)
formula_col(mo, 19, MO0, MO1, '=IF($G{r}=0,"",$R{r}/$G{r})', PCT)
formula_col(mo, 20, MO0, MO1, "=$G{r}-$H{r}-$P{r}+$Q{r}", MONEY)
formula_col(mo, 21, MO0, MO1, f"=IF($A{{r}}>TODAY(),\"\",SUM('NW grid'!$B{{r}}:${L(1 + (AC1 - AC0 + 1))}{{r}}))", MONEY)

# ===============================================================================================
# NW grid (engine): rows = months, columns = accounts
title(nw, "NET WORTH GRID — engine (do not edit)", "Each account's latest balance at each month end "
      "(debts negative). Feeds the net worth history.")
nw["A4"], nw["A5"] = "sign →", "Month ↓ / account →"
for j in range(AC1 - AC0 + 1):
    col = L(2 + j)
    acc_row = AC0 + j
    nw[f"{col}4"] = f'=IF(Accounts!$C${acc_row}="Debt",-1,1)'
    nw[f"{col}5"] = f'=IF(Accounts!$A${acc_row}="","",Accounts!$A${acc_row})'
    nw[f"{col}5"].font, nw[f"{col}5"].fill, nw[f"{col}5"].alignment = F_HEAD, FILL_CALC_HEAD, CENTER
    nw.column_dimensions[col].width = 12
nw.column_dimensions["A"].width = 12
for r in range(MO0, MO1 + 1):
    nw[f"A{r}"] = f"=Months!$A${r}"
    nw[f"A{r}"].number_format = MONTH
    for j in range(AC1 - AC0 + 1):
        col = L(2 + j)
        last = f"_xlfn.MAXIFS({BL['A']},{BL['B']},{col}$5,{BL['A']},\"<=\"&MIN(Months!$B${r},TODAY()))"
        c = nw[f"{col}{r}"]
        c.value = f'=IF({col}$5="",0,{col}$4*SUMIFS({BL["C"]},{BL["B"]},{col}$5,{BL["A"]},{last}))'
        c.number_format = MONEY
nw.freeze_panes = "B6"

# ===============================================================================================
# Dashboard
title(dash, "MONEY DASHBOARD", "Everything connected: transactions, recurring items, funds and net worth.")
dash["A1"] = f'="MONEY DASHBOARD"&IF({ "Settings!$C$4" }="",""," — "&Settings!$C$4)'
dash.column_dimensions["A"].width = 2
for col, w in zip("BCDEFGHIJ", (34, 15, 15, 15, 15, 15, 15, 15, 15)):
    dash.column_dimensions[col].width = w
dash["B4"] = "Look at month (leave empty = this month)"
dash["B4"].font = F_BOLD
dash["C4"].fill, dash["C4"].font, dash["C4"].border, dash["C4"].number_format = FILL_INPUT, F_INPUT, BOX, MONTH
dash["D4"] = '=IF(C4="",DATE(YEAR(TODAY()),MONTH(TODAY()),1),DATE(YEAR(C4),MONTH(C4),1))'
dash["D4"].number_format = MONTH
dash["D4"].font = F_BOLD
dash["E4"] = f'=IF(ISNA(MATCH(D4,{MO["A"]},0)),"⚠ This month is outside the sheet range: change \'First month\' in Settings","")'
dash["E4"].font = Font(name=ARIAL, size=10, bold=True, color="C00000")
MI = f"MATCH($D$4,{MO['A']},0)"

dash["B6"] = "THIS MONTH VS LAST 12 MONTHS"
dash["B6"].font = F_H2
for c, h in zip("BCD", ("", "This month", "Last 12 months")):
    cell = dash[f"{c}7"]
    cell.value, cell.font, cell.fill, cell.alignment = h, F_HEAD, FILL_HEAD, CENTER
KPI = [("Income", "G"), ("Expenses", "H"), ("Saved (income − expenses)", "R"), ("Savings rate", None),
       ("Put into funds", "P"), ("Paid from funds", "Q"), ("Left over to spend", "T")]
for i, (label, col) in enumerate(KPI):
    r = 8 + i
    dash[f"B{r}"] = label
    dash[f"B{r}"].font = F_BOLD
    if col:
        dash[f"C{r}"] = f"=IFERROR(INDEX({MO[col]},{MI}),0)"
        dash[f"D{r}"] = f'=SUMIFS({MO[col]},{MO["A"]},">"&EDATE($D$4,-12),{MO["A"]},"<="&$D$4)'
        fmt = MONEY
    else:
        dash[f"C{r}"] = '=IF(C8=0,"",C10/C8)'
        dash[f"D{r}"] = '=IF(D8=0,"",D10/D8)'
        fmt = PCT
    for c in "CD":
        dash[f"{c}{r}"].number_format = fmt
        dash[f"{c}{r}"].font = F_KPI if label.startswith("Left over") else F_BOLD
        dash[f"{c}{r}"].fill = FILL_KPI
        dash[f"{c}{r}"].border = BOX
dash["B15"] = "Left over to spend = income − expenses − put into funds + expenses your funds paid for."
dash["B15"].font = F_SUB

# Net worth block
dash["F6"] = "NET WORTH"
dash["F6"].font = F_H2
AC_C, AC_F, AC_G, AC_I, AC_H, AC_A, AC_E = (rng("Accounts", c, AC0, AC1) for c in "CFGIHAE")
for i, (label, f, fmt) in enumerate([
    ("Assets", f'=SUMIFS({AC_F},{AC_C},"Asset")', MONEY),
    ("Debts", f'=SUMIFS({AC_F},{AC_C},"Debt")', MONEY),
    ("Net worth", "=G8-G9", MONEY),
    ("30-day change", f'=IF(COUNTIF({AC_H},">0")=0,"",SUM({AC_G})-SUM({AC_I}))', '+#,##0.00;[Red]-#,##0.00;"-"'),
    ("Need an update", f'=COUNTIF({rng("Accounts", "K", AC0, AC1)},"Update me")', "0"),
]):
    r = 8 + i
    dash[f"F{r}"] = label
    dash[f"F{r}"].font = F_BOLD
    dash[f"G{r}"] = f
    dash[f"G{r}"].number_format = fmt
    dash[f"G{r}"].fill, dash[f"G{r}"].border = FILL_KPI, BOX
    dash[f"G{r}"].font = F_KPI if label == "Net worth" else F_BOLD

# Funds table
FR = 17
dash[f"B{FR - 1}"] = "FUNDS"
dash[f"B{FR - 1}"].font = F_H2
for c, h in zip("BCDEFGH", ("Fund", "Balance", "Target", "Progress", "Needed / month", "Automation", "Status")):
    cell = dash[f"{c}{FR}"]
    cell.value, cell.font, cell.fill, cell.alignment = h, F_HEAD, FILL_HEAD, CENTER
for i in range(FD1 - FD0 + 1):
    r, src = FR + 1 + i, FD0 + i
    dash[f"B{r}"] = f'=IF(Funds!$A${src}="","",Funds!$A${src})'
    dash[f"C{r}"] = f'=IF(Funds!$A${src}="","",Funds!$N${src})'
    dash[f"D{r}"] = f'=IF(Funds!$A${src}="","",Funds!$C${src})'
    dash[f"E{r}"] = f'=IF(Funds!$A${src}="","",Funds!$O${src})'
    dash[f"F{r}"] = f'=IF(Funds!$A${src}="","",Funds!$Q${src})'
    dash[f"G{r}"] = (f'=IF(Funds!$A${src}="","",IF(AND(N(Funds!$E${src})=0,N(Funds!$G${src})=0),"by hand",'
                     f'TRIM(IF(N(Funds!$E${src})>0,TEXT(Funds!$E${src},"#,##0")&" / month","")'
                     f'&IF(AND(N(Funds!$E${src})>0,N(Funds!$G${src})>0)," + ","")'
                     f'&IF(N(Funds!$G${src})>0,TEXT(Funds!$G${src},"0%")&" of income",""))))')
    dash[f"H{r}"] = f'=IF(Funds!$A${src}="","",Funds!$S${src})'
    for c, fmt in zip("CDEF", (MONEY, MONEY, PCT, MONEY)):
        dash[f"{c}{r}"].number_format = fmt
FL = FR + (FD1 - FD0 + 1)
dash.conditional_formatting.add(f"E{FR + 1}:E{FL}", DataBarRule(start_type="num", start_value=0, end_type="num",
                                                                end_value=1, color="5B9BD5"))
dash.conditional_formatting.add(f"H{FR + 1}:H{FL}", FormulaRule(
    formula=[f'OR(ISNUMBER(SEARCH("Overspent",$H{FR + 1})),ISNUMBER(SEARCH("Behind",$H{FR + 1})))'],
    font=Font(name=ARIAL, bold=True, color="C00000")))

# Spending by category (selected month)
CR = 17
dash[f"J{CR - 1}"] = "SPENDING BY CATEGORY (selected month)"
dash[f"J{CR - 1}"].font = F_H2
dash.column_dimensions["J"].width = 22
dash.column_dimensions["K"].width = 14
for c, h in zip("JK", ("Category", "Spent")):
    cell = dash[f"{c}{CR}"]
    cell.value, cell.font, cell.fill, cell.alignment = h, F_HEAD, FILL_HEAD, CENTER
UPTO_D = "MIN(EOMONTH($D$4,0),TODAY())"
BILL_D = f'($D$4+{R["I"]}-1)'
RC_COND_D = (f'({R["F"]}>0)*({R["F"]}<={BILL_D})*((({R["G"]}="")+({R["G"]}>={BILL_D}))>0)*({BILL_D}<=TODAY())'
             f'*((({R["E"]}<>"Yearly")+(MONTH({R["F"]})=MONTH($D$4)))>0)')
for i in range(CT1 - CT0 + 1):
    r, src = CR + 1 + i, CT0 + i
    dash[f"J{r}"] = f'=IF(Settings!$F${src}="","",Settings!$F${src})'
    dash[f"K{r}"] = (f'=IF($J{r}="","",SUMIFS({T["E"]},{T["B"]},"Expense",{T["C"]},$J{r},{T["A"]},">="&$D$4,'
                     f'{T["A"]},"<="&{UPTO_D})+SUMPRODUCT({R["D"]}*({R["B"]}="Expense")*({R["C"]}=$J{r})*{RC_COND_D}))')
    dash[f"K{r}"].number_format = MONEY
dash.conditional_formatting.add(f"K{CR + 1}:K{CR + CT1 - CT0 + 1}", DataBarRule(
    start_type="num", start_value=0, end_type="max", color="F4B183"))

# 12-month table + charts
HR = FL + 3
dash[f"B{HR - 1}"] = "LAST 12 MONTHS"
dash[f"B{HR - 1}"].font = F_H2
for c, h in zip("BCDEFG", ("Month", "Income", "Expenses", "Into funds", "Left over", "Net worth")):
    cell = dash[f"{c}{HR}"]
    cell.value, cell.font, cell.fill, cell.alignment = h, F_HEAD, FILL_HEAD, CENTER
for i in range(12):
    r = HR + 1 + i
    dash[f"B{r}"] = f"=EDATE($D$4,{i - 11})"
    dash[f"B{r}"].number_format = MONTH
    for c, src in zip("CDEFG", "GHPTU"):
        dash[f"{c}{r}"] = f'=IFERROR(INDEX({MO[src]},MATCH($B{r},{MO["A"]},0)),0)'
        dash[f"{c}{r}"].number_format = MONEY
bar = BarChart()
bar.type, bar.title, bar.height, bar.width = "col", "Income vs expenses", 7.5, 15
bar.add_data(Reference(dash, min_col=3, max_col=4, min_row=HR, max_row=HR + 12), titles_from_data=True)
bar.set_categories(Reference(dash, min_col=2, min_row=HR + 1, max_row=HR + 12))
bar.y_axis.numFmt = "#,##0"
dash.add_chart(bar, f"B{HR + 15}")
line = LineChart()
line.title, line.height, line.width = "Net worth", 7.5, 15
line.add_data(Reference(dash, min_col=7, min_row=HR, max_row=HR + 12), titles_from_data=True)
line.set_categories(Reference(dash, min_col=2, min_row=HR + 1, max_row=HR + 12))
line.y_axis.numFmt = "#,##0"
for sr in line.series:
    sr.smooth = False
dash.add_chart(line, f"F{HR + 15}")
dash.freeze_panes = "A5"

# ===============================================================================================
# How to use
g = guide
g.column_dimensions["A"].width = 2
g.column_dimensions["B"].width = 30
g.column_dimensions["C"].width = 95
row = 1


def gh(text: str) -> None:
    global row
    row += 1
    g.cell(row=row, column=2, value=text).font = F_H2
    row += 1


def gl(label: str, text: str, bold_label: bool = True) -> None:
    global row
    a = g.cell(row=row, column=2, value=label)
    a.font, a.alignment = (F_BOLD if bold_label else F_BASE), WRAP
    b = g.cell(row=row, column=3, value=text)
    b.font, b.alignment = F_BASE, WRAP
    g.row_dimensions[row].height = max(15, 15 * (len(text) // 105 + 1))
    row += 1


g["B1"] = "MONEY COCKPIT — how to use"
g["B1"].font = F_TITLE
row = 2
g.cell(row=row, column=2, value="Your income, spending, savings funds and net worth in one place, all connected. "
       "You type a few things; everything else updates by itself.").font = F_SUB

gh("1. The colours")
c = g.cell(row=row, column=2, value="Yellow cell, blue text")
c.fill, c.font = FILL_INPUT, F_INPUT
g.cell(row=row, column=3, value="You type here.").font = F_BASE
row += 1
gl("White cell, black text", "Calculated. Do not type over it (the formula would be lost).", False)
gl("Dark-blue header", "A column you fill in.", False)
gl("Light-blue header", "A calculated column.", False)
gl("Grey tabs (Months, NW grid)", "The engine behind the Dashboard. Look, don't touch.", False)

gh("2. The tabs")
gl("Dashboard", "Your money at a glance: this month vs the last 12 months, net worth, every fund, spending by "
   "category and two charts. Change the yellow 'Look at month' cell to look at any past month.")
gl("Transactions", "Every income or expense, one line each. Optional 'Fund' column: an expense PAID FROM a fund "
   "(the flight from your Travel fund) or an income that goes INTO a fund (Eid money into Gifts & Eid).")
gl("Recurring", "Things that repeat: salary, rent, phone, gym, subscriptions. Type them once with a Start date "
   "(and an End date when they stop); they are counted every month (or year) automatically.")
gl("Funds", "Savings pots for a purpose. Each fund can fill itself: a fixed amount every month on a day you "
   "choose, and/or a % of every income. Shows balance, progress, what is left and what you need per month/week.")
gl("Fund moves", "Money you put in (+) or take out (−) of a fund by hand.")
gl("Accounts", "What you own (current account, savings, investments, crypto, car…) and owe (loans, credit card…).")
gl("Balances", "The balance of an account on a date. The most recent one counts for net worth.")
gl("Settings", "Your name, currency, the first month of the sheet, and the drop-down lists (categories, fund kinds, "
   "account types). Add your own categories at the bottom of a list.")

gh("3. First time (15 minutes)")
for step, text in [
    ("1. Settings", "Type your name and currency. Set 'First month of this sheet' to the first month you will log."),
    ("2. Recurring", "Add salary, rent and subscriptions with their Start date."),
    ("3. Funds", "Create your funds (Emergency, Travel, Gifts & Eid, Hajj…). Give each a Target, maybe a Deadline. "
                 "To automate: 'Put in every month' + 'On day', and/or '% of every income' (type 10% as 10%), "
                 "and ALWAYS an 'Automation starts' date."),
    ("4. Accounts + Balances", "List your accounts, then one line per account in Balances with today's balance."),
]:
    gl(step, text)

gh("4. The routine")
gl("Whenever you spend or earn", "Add a line in Transactions. Paid with fund money? Pick the fund in 'Fund'.")
gl("Once a month", "Balances: one new line per account. Dashboard: read 'Left over to spend', the funds' status and "
   "net worth. Accounts flagged 'Update me' have not been updated for 45 days.")

gh("5. How the numbers are calculated")
for label, text in [
    ("Income / Expenses", "Transactions + recurring items of that month. Only days that have passed count: an entry "
                          "dated next week is ignored until next week."),
    ("Saved", "Income − Expenses. This is what you kept, funds included."),
    ("Savings rate", "Saved ÷ Income."),
    ("Put into funds", "Automatic monthly amounts + shares of income + money added by hand + income routed into a fund."),
    ("Paid from funds", "Expenses paid with fund money + money taken out of a fund by hand."),
    ("Left over to spend", "Income − Expenses − Put into funds + Paid from funds. A flight paid from your Travel fund "
                           "does not reduce what you have left to spend: the fund paid for it."),
    ("Fund balance", "Automatic monthly so far + share of income so far + by hand (in − out) + income into the fund "
                     "− expenses paid from the fund."),
    ("Automatic monthly", "The amount, on the chosen day of every month, from 'Automation starts' up to today."),
    ("Share of income", "The % of every income that is not already routed to a fund, from the month automation starts. "
                        "All funds together should not go above 100% (the Funds total warns you)."),
    ("Needed / month", "What is left ÷ months until the deadline (this month included). Needed / week: same per week. "
                       "Status 'Behind schedule' = your automatic monthly amount is lower than what is needed."),
    ("Net worth", "Assets − debts, using each account's most recent balance. '30-day change' compares with the "
                  "balances you had 30 days ago."),
    ("Recurring billing day", "The day of the Start date. Days 29-31 are billed on the 28th so every month has one."),
]:
    gl(label, text)

gh("6. Good to know")
gl("Funds are labels", "A fund is money that sits in one of your accounts with a purpose. It does not add to net worth.")
gl("Changing an automation", "The sheet recalculates from 'Automation starts'. To change an amount without rewriting "
   "the past: add a Fund move with what the old rule put in, then set 'Automation starts' to today with the new amount.")
gl("Taking out more than you have", "Allowed (life happens), but the fund shows 'Overspent' in red.")
gl("Deleting a line", "Clear the cells (select → Delete). Do not delete rows or columns: formulas point at them.")
gl("Capacity", "2000 transactions, 100 recurring items, 20 funds, 1000 fund moves, 30 accounts, 3000 balances, "
   "60 months from the first month. Need more? Start a new copy, or ask whoever set this up.")

gh("7. Example rows (format only — NOT counted anywhere)")
examples = [
    ("Transactions", ["Date", "Type", "Category", "Label", "Amount", "Fund", "Notes"],
     ["05/11/2026", "Expense", "Travel", "Flight Paris-Jakarta", "320.00", "Travel fund", "paid from the fund"]),
    ("Recurring", ["Label", "Type", "Category", "Amount", "Every", "Start", "End", "Fund"],
     ["Rent", "Expense", "Housing", "750.00", "Monthly", "01/09/2026", "", ""]),
    ("Funds", ["Fund name", "Kind", "Target", "Deadline", "Every month", "On day", "% of income", "Automation starts"],
     ["Travel fund", "Travel", "2400.00", "15/02/2027", "200.00", "1", "0%", "01/11/2026"]),
    ("Fund moves", ["Date", "Fund", "Amount", "Note"], ["10/11/2026", "Gifts & Eid", "-45.00", "Wedding gift"]),
    ("Accounts", ["Account name", "Type", "Bank / where"], ["Livret A", "Savings", "My bank"]),
    ("Balances", ["Date", "Account", "Balance / amount owed", "Note"], ["30/11/2026", "Livret A", "6200.00", ""]),
]
for tab, heads, vals in examples:
    g.cell(row=row, column=2, value=tab).font = F_BOLD
    g.cell(row=row, column=3, value="   |   ".join(heads)).font = F_SUB
    row += 1
    cell = g.cell(row=row, column=3, value="   |   ".join(v if v else "(empty)" for v in vals))
    cell.font, cell.fill = F_BASE, FILL_EX
    row += 1
g.freeze_panes = "A3"

# ---- final touches ----------------------------------------------------------------------------
for ws in wb.worksheets:
    ws.sheet_view.zoomScale = 100
from openpyxl.workbook.properties import CalcProperties
wb.calculation = CalcProperties(fullCalcOnLoad=True)  # Excel/Numbers/Sheets recompute on open
wb.active = 0
wb.save(OUT)
print("saved", OUT)

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference

excel_path = 'WGC-DTMP Custom Enrichment Analysis/WGC_DTMP_Enrichment_Distribution.xlsx'
df = pd.read_excel(excel_path)

df['SOURCE_TYPE'] = df['SOURCE_TYPE'].astype(str)

for col in ['METRIC_TYPE', 'ATTRIBUTE', 'FIELD_VALUE', 'SOURCE_TYPE']:
    df[col] = df[col].astype(str).str.strip()

wb = openpyxl.Workbook()

NAVY_HEADER = '0A192F'
NAVY_SUBHEADER = '134074'
GOLD_ACCENT = 'D4AF37'
TEAL_ACCENT = '1E56A0'
LIGHT_BLUE_BG = 'F0F4F8'
ZEBRA_FILL = 'F9FAFB'
WHITE = 'FFFFFF'
BORDER_COLOR = 'D9D9D9'
DARK_TEXT = '111111'

font_title = Font(name='Calibri', size=15, bold=True, color=WHITE)
font_subtitle = Font(name='Calibri', size=10, italic=True, color=GOLD_ACCENT)
font_section = Font(name='Calibri', size=13, bold=True, color=NAVY_HEADER)
font_group_hdr = Font(name='Calibri', size=11, bold=True, color=WHITE)
font_tbl_header = Font(name='Calibri', size=11, bold=True, color=WHITE)
font_bold = Font(name='Calibri', size=11, bold=True, color=DARK_TEXT)
font_regular = Font(name='Calibri', size=11, color=DARK_TEXT)
font_small = Font(name='Calibri', size=9, italic=True, color='555555')

fill_navy = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type='solid')
fill_subnavy = PatternFill(start_color=NAVY_SUBHEADER, end_color=NAVY_SUBHEADER, fill_type='solid')
fill_gold = PatternFill(start_color=GOLD_ACCENT, end_color=GOLD_ACCENT, fill_type='solid')
fill_teal = PatternFill(start_color=TEAL_ACCENT, end_color=TEAL_ACCENT, fill_type='solid')
fill_light_blue = PatternFill(start_color=LIGHT_BLUE_BG, end_color=LIGHT_BLUE_BG, fill_type='solid')
fill_zebra = PatternFill(start_color=ZEBRA_FILL, end_color=ZEBRA_FILL, fill_type='solid')

thin_side = Side(border_style='thin', color=BORDER_COLOR)
thick_bottom = Side(border_style='medium', color=NAVY_HEADER)
double_bottom = Side(border_style='double', color=NAVY_HEADER)

border_cell = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
border_header = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thick_bottom)
border_total = Border(left=thin_side, right=thin_side, top=thin_side, bottom=double_bottom)

align_left = Alignment(horizontal='left', vertical='center')
align_right = Alignment(horizontal='right', vertical='center')
align_center = Alignment(horizontal='center', vertical='center')
align_header = Alignment(horizontal='center', vertical='center', wrap_text=True)

years_order = [
    '2019 Dell Technologies Match Play',
    '2020 Dell Technologies Match Play',
    '2021 Dell Technologies Match Play',
    '2022 Dell Technologies Match Play',
    '2023 Dell Technologies Match Play',
    'Overall'
]

# -------------------------------------------------------------------------
# TAB 1: EXECUTIVE OVERVIEW
# -------------------------------------------------------------------------
ws_exec = wb.active
ws_exec.title = 'Executive Overview'
ws_exec.views.sheetView[0].showGridLines = True

ws_exec.merge_cells('A1:I1')
ws_exec.merge_cells('A2:I2')
for r in range(1, 3):
    for c in range(1, 10):
        cell = ws_exec.cell(row=r, column=c)
        cell.fill = fill_navy

ws_exec.cell(row=1, column=1).value = 'DELL TECHNOLOGIES MATCH PLAY - DEMOGRAPHIC & GEOGRAPHIC ENRICHMENT'
ws_exec.cell(row=1, column=1).font = font_title
ws_exec.cell(row=1, column=1).alignment = Alignment(horizontal='left', vertical='center', indent=1)

ws_exec.cell(row=2, column=1).value = 'Client Executive Summary & Audience Insights (2019 - 2023) | PGA TOUR Analytics'
ws_exec.cell(row=2, column=1).font = font_subtitle
ws_exec.cell(row=2, column=1).alignment = Alignment(horizontal='left', vertical='center', indent=1)

ws_exec.row_dimensions[1].height = 25
ws_exec.row_dimensions[2].height = 18

ws_exec.cell(row=4, column=1).value = 'KEY AUDIENCE METRICS & PROFILE HIGHLIGHTS'
ws_exec.cell(row=4, column=1).font = font_section

cards = [
    ('Enriched Ticketholders', '130,245', 'Total unique profile records', 1),
    ('High Net Worth (> )', '68.3%', '79.7% in 2019 | 68.3% overall', 3),
    ('Household Income > ', '71.8%', '11.3% earn + annually', 5),
    ('Top Market (Austin DMA)', '72.4%', '122,732 ticketholder records', 7)
]

for label, val, sub, col_idx in cards:
    ws_exec.merge_cells(start_row=5, start_column=col_idx, end_row=5, end_column=col_idx+1)
    c_hdr = ws_exec.cell(row=5, column=col_idx)
    c_hdr.value = label.upper()
    c_hdr.font = Font(name='Calibri', size=9, bold=True, color=WHITE)
    c_hdr.fill = fill_teal
    c_hdr.alignment = align_center

    ws_exec.merge_cells(start_row=6, start_column=col_idx, end_row=6, end_column=col_idx+1)
    c_val = ws_exec.cell(row=6, column=col_idx)
    c_val.value = val
    c_val.font = Font(name='Calibri', size=16, bold=True, color=NAVY_HEADER)
    c_val.fill = fill_light_blue
    c_val.alignment = align_center

    ws_exec.merge_cells(start_row=7, start_column=col_idx, end_row=7, end_column=col_idx+1)
    c_sub = ws_exec.cell(row=7, column=col_idx)
    c_sub.value = sub
    c_sub.font = font_small
    c_sub.fill = fill_light_blue
    c_sub.alignment = align_center

    for r in range(5, 8):
        for c in range(col_idx, col_idx+2):
            ws_exec.cell(row=r, column=c).border = border_cell

ws_exec.cell(row=9, column=1).value = 'STRATEGIC FINDINGS & EXECUTIVE TAKEAWAYS'
ws_exec.cell(row=9, column=1).font = font_section

takeaways = [
    ('Affluent & High Net Worth Base', 'Over 68% of profiled ticketholders hold net worth exceeding ,000, and 71.8% earn over ,000 in household income (with 11.3% earning over  annually). This highlights an exceptionally premium audience ideal for corporate partnerships and high-end hospitality.'),
    ('Executive Leadership & Decision Makers', '62.4% of profiled ticketholders hold Professional (25.2%) or Upper Management (37.2%) positions. Combined with a 74.8% top-tier credit score (750+), this audience reflects influential corporate decision-makers.'),
    ('Geographic Concentration & Key Feeders', 'The Austin DMA represents 72.4% of total ticketholder records, with Texas overall accounting for 85.7%. Key secondary markets include Dallas-Ft. Worth (4.2%), Houston (3.2%), San Antonio (2.1%), San Francisco (1.7%), and Florida (4.1%).'),
    ('Demographic Evolution (2019 - 2023)', 'While core attendees remain 45-64 years old (~49%), the 25-34 age bracket expanded from 2.8% in 2019 to 9.6% overall, reflecting growing engagement among next-generation fans.')
]

row_curr = 10
for title, body in takeaways:
    ws_exec.cell(row=row_curr, column=1).value = f'•  {title}:'
    ws_exec.cell(row=row_curr, column=1).font = Font(name='Calibri', size=11, bold=True, color=NAVY_HEADER)
    
    ws_exec.merge_cells(start_row=row_curr, start_column=2, end_row=row_curr, end_column=9)
    c_body = ws_exec.cell(row=row_curr, column=2)
    c_body.value = body
    c_body.font = font_regular
    c_body.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
    ws_exec.row_dimensions[row_curr].height = 36
    row_curr += 1

row_curr += 1
ws_exec.cell(row=row_curr, column=1).value = 'AGE RANGE DISTRIBUTION COMPARISON'
ws_exec.cell(row=row_curr, column=1).font = font_section
row_curr += 1

age_df = df[df['ATTRIBUTE'] == 'Age_Range']
pv_age = age_df.pivot_table(index='FIELD_VALUE', columns='SOURCE_TYPE', values='FIELD_DISTRIBUTION', aggfunc='first')
pv_age = pv_age[[y for y in years_order if y in pv_age.columns]]

headers = ['Age Range', '2019', '2020', '2021', '2022', '2023', 'Overall Total']
for c_idx, h in enumerate(headers, 1):
    cell = ws_exec.cell(row=row_curr, column=c_idx)
    cell.value = h
    cell.font = font_tbl_header
    cell.fill = fill_navy
    cell.alignment = align_header
    cell.border = border_header
ws_exec.row_dimensions[row_curr].height = 20

tbl1_start_row = row_curr
row_curr += 1

for idx_val, row_data in pv_age.iterrows():
    ws_exec.cell(row=row_curr, column=1).value = str(idx_val)
    ws_exec.cell(row=row_curr, column=1).font = font_bold
    ws_exec.cell(row=row_curr, column=1).alignment = align_left
    ws_exec.cell(row=row_curr, column=1).border = border_cell
    
    for c_idx, val in enumerate(row_data, 2):
        cell = ws_exec.cell(row=row_curr, column=c_idx)
        cell.value = float(val) if pd.notnull(val) else 0.0
        cell.number_format = '0.0%'
        cell.font = font_regular
        cell.alignment = align_right
        cell.border = border_cell
        if c_idx == 7:
            cell.fill = fill_light_blue
            cell.font = font_bold
    ws_exec.row_dimensions[row_curr].height = 19
    row_curr += 1

tbl1_end_row = row_curr - 1

chart_age = BarChart()
chart_age.type = 'col'
chart_age.style = 10
chart_age.title = 'Age Distribution Across Tournament Years'
chart_age.y_axis.title = '% Distribution'
chart_age.x_axis.title = 'Age Range'
chart_age.height = 10
chart_age.width = 17

data_ref = Reference(ws_exec, min_col=2, min_row=tbl1_start_row, max_col=7, max_row=tbl1_end_row)
cats_ref = Reference(ws_exec, min_col=1, min_row=tbl1_start_row+1, max_row=tbl1_end_row)
chart_age.add_data(data_ref, titles_from_data=True)
chart_age.set_categories(cats_ref)

ws_exec.add_chart(chart_age, f'A{row_curr+2}')

# -------------------------------------------------------------------------
# TAB 2: DEMOGRAPHIC DISTRIBUTION
# -------------------------------------------------------------------------
ws_demo = wb.create_sheet(title='Demographic Distribution')
ws_demo.views.sheetView[0].showGridLines = True

ws_demo.merge_cells('A1:G1')
ws_demo.merge_cells('A2:G2')
for r in range(1, 3):
    for c in range(1, 8):
        cell = ws_demo.cell(row=r, column=c)
        cell.fill = fill_navy

ws_demo.cell(row=1, column=1).value = 'DEMOGRAPHIC ENRICHMENT DISTRIBUTION BY ATTRIBUTE'
ws_demo.cell(row=1, column=1).font = font_title
ws_demo.cell(row=1, column=1).alignment = Alignment(horizontal='left', vertical='center', indent=1)

ws_demo.cell(row=2, column=1).value = 'Side-by-Side Analysis Across Tournament Years (2019 - 2023) and Overall Benchmark'
ws_demo.cell(row=2, column=1).font = font_subtitle
ws_demo.cell(row=2, column=1).alignment = Alignment(horizontal='left', vertical='center', indent=1)

ws_demo.row_dimensions[1].height = 25
ws_demo.row_dimensions[2].height = 18

demo_attributes = [
    ('Age_Range', 'Age Range Distribution'),
    ('AA_Gender', 'Gender Profile'),
    ('AA_Marital_Status', 'Marital Status'),
    ('AA_Children_HH', 'Presence of Children in Household'),
    ('AA_Home_Owner', 'Home Ownership Status'),
    ('AA_Income_HH', 'Household Income Brackets'),
    ('AA_Net_Worth_HH', 'Household Net Worth Tiers'),
    ('AA_Credit_Range', 'Credit Score Range'),
    ('AA_Occupation_Category', 'Occupation & Professional Category')
]

row_d = 4

for attr_key, attr_title in demo_attributes:
    sub_df = df[df['ATTRIBUTE'] == attr_key]
    if len(sub_df) == 0:
        continue

    ws_demo.merge_cells(start_row=row_d, start_column=1, end_row=row_d, end_column=7)
    c_ghdr = ws_demo.cell(row=row_d, column=1)
    c_ghdr.value = f'  {attr_title.upper()}'
    c_ghdr.font = font_group_hdr
    c_ghdr.fill = fill_subnavy
    c_ghdr.alignment = Alignment(horizontal='left', vertical='center')
    ws_demo.row_dimensions[row_d].height = 22
    row_d += 1

    hdrs = ['Field Value', '2019', '2020', '2021', '2022', '2023', 'Overall Total']
    for c_i, h in enumerate(hdrs, 1):
        cell = ws_demo.cell(row=row_d, column=c_i)
        cell.value = h
        cell.font = font_tbl_header
        cell.fill = fill_navy
        cell.alignment = align_header
        cell.border = border_header
    ws_demo.row_dimensions[row_d].height = 20
    row_d += 1

    pv_attr = sub_df.pivot_table(index='FIELD_VALUE', columns='SOURCE_TYPE', values='FIELD_DISTRIBUTION', aggfunc='first')
    pv_attr = pv_attr[[y for y in years_order if y in pv_attr.columns]]

    r_count = 0
    for f_val, r_data in pv_attr.iterrows():
        ws_demo.cell(row=row_d, column=1).value = str(f_val)
        ws_demo.cell(row=row_d, column=1).font = font_bold
        ws_demo.cell(row=row_d, column=1).alignment = align_left
        ws_demo.cell(row=row_d, column=1).border = border_cell

        is_zebra = (r_count % 2 == 1)
        r_count += 1

        for c_i, val in enumerate(r_data, 2):
            cell = ws_demo.cell(row=row_d, column=c_i)
            cell.value = float(val) if pd.notnull(val) else 0.0
            cell.number_format = '0.0%'
            cell.font = font_regular
            cell.alignment = align_right
            cell.border = border_cell
            if c_i == 7:
                cell.fill = fill_light_blue
                cell.font = font_bold
            elif is_zebra:
                cell.fill = fill_zebra
        ws_demo.row_dimensions[row_d].height = 19
        row_d += 1

    row_d += 1

# -------------------------------------------------------------------------
# TAB 3: GEOGRAPHIC BREAKDOWN
# -------------------------------------------------------------------------
ws_geo = wb.create_sheet(title='Geographic Breakdown')
ws_geo.views.sheetView[0].showGridLines = True

ws_geo.merge_cells('A1:G1')
ws_geo.merge_cells('A2:G2')
for r in range(1, 3):
    for c in range(1, 8):
        cell = ws_geo.cell(row=r, column=c)
        cell.fill = fill_navy

ws_geo.cell(row=1, column=1).value = 'GEOGRAPHIC DISTRIBUTION & MARKET BREAKDOWN'
ws_geo.cell(row=1, column=1).font = font_title
ws_geo.cell(row=1, column=1).alignment = Alignment(horizontal='left', vertical='center', indent=1)

ws_geo.cell(row=2, column=1).value = 'Top Designated Market Areas (DMAs) & States of Dell Match Play Ticketholders'
ws_geo.cell(row=2, column=1).font = font_subtitle
ws_geo.cell(row=2, column=1).alignment = Alignment(horizontal='left', vertical='center', indent=1)

ws_geo.row_dimensions[1].height = 25
ws_geo.row_dimensions[2].height = 18

ws_geo.merge_cells('A4:G4')
c_dma_hdr = ws_geo.cell(row=4, column=1)
c_dma_hdr.value = '  TOP 15 DESIGNATED MARKET AREAS (DMAS)'
c_dma_hdr.font = font_group_hdr
c_dma_hdr.fill = fill_subnavy
c_dma_hdr.alignment = Alignment(horizontal='left', vertical='center')
ws_geo.row_dimensions[4].height = 22

dma_df = df[df['ATTRIBUTE'] == 'DMA_Name']
dma_overall = dma_df[dma_df['SOURCE_TYPE'] == 'Overall'].sort_values('FIELD_RECORDS', ascending=False).head(15)

hdrs_geo = ['DMA Market', 'Enriched Fan Records', '% of Overall Audience', '2019 %', '2021 %', '2022 %', '2023 %']
for c_i, h in enumerate(hdrs_geo, 1):
    cell = ws_geo.cell(row=5, column=c_i)
    cell.value = h
    cell.font = font_tbl_header
    cell.fill = fill_navy
    cell.alignment = align_header
    cell.border = border_header
ws_geo.row_dimensions[5].height = 20

row_g = 6
for _, r_dma in dma_overall.iterrows():
    d_name = r_dma['FIELD_VALUE']
    d_recs = r_dma['FIELD_RECORDS']
    d_dist = r_dma['FIELD_DISTRIBUTION']

    ws_geo.cell(row=row_g, column=1).value = str(d_name)
    ws_geo.cell(row=row_g, column=1).font = font_bold
    ws_geo.cell(row=row_g, column=1).alignment = align_left
    ws_geo.cell(row=row_g, column=1).border = border_cell

    ws_geo.cell(row=row_g, column=2).value = int(d_recs)
    ws_geo.cell(row=row_g, column=2).number_format = '#,##0'
    ws_geo.cell(row=row_g, column=2).font = font_bold
    ws_geo.cell(row=row_g, column=2).alignment = align_right
    ws_geo.cell(row=row_g, column=2).border = border_cell

    ws_geo.cell(row=row_g, column=3).value = float(d_dist)
    ws_geo.cell(row=row_g, column=3).number_format = '0.0%'
    ws_geo.cell(row=row_g, column=3).font = font_bold
    ws_geo.cell(row=row_g, column=3).alignment = align_right
    ws_geo.cell(row=row_g, column=3).fill = fill_light_blue
    ws_geo.cell(row=row_g, column=3).border = border_cell

    for c_i, yr_str in enumerate(['2019 Dell Technologies Match Play', '2021 Dell Technologies Match Play', '2022 Dell Technologies Match Play', '2023 Dell Technologies Match Play'], 4):
        yr_row = dma_df[(dma_df['FIELD_VALUE'] == d_name) & (dma_df['SOURCE_TYPE'] == yr_str)]
        val = yr_row['FIELD_DISTRIBUTION'].values[0] if len(yr_row) > 0 else 0.0
        cell = ws_geo.cell(row=row_g, column=c_i)
        cell.value = float(val) if pd.notnull(val) else 0.0
        cell.number_format = '0.0%'
        cell.font = font_regular
        cell.alignment = align_right
        cell.border = border_cell

    ws_geo.row_dimensions[row_g].height = 19
    row_g += 1

row_g += 2
ws_geo.merge_cells(start_row=row_g, start_column=1, end_row=row_g, end_column=7)
c_st_hdr = ws_geo.cell(row=row_g, column=1)
c_st_hdr.value = '  TOP 15 STATES BY AUDIENCE VOLUME'
c_st_hdr.font = font_group_hdr
c_st_hdr.fill = fill_subnavy
c_st_hdr.alignment = Alignment(horizontal='left', vertical='center')
ws_geo.row_dimensions[row_g].height = 22
row_g += 1

st_df = df[df['ATTRIBUTE'] == 'State']
st_overall = st_df[st_df['SOURCE_TYPE'] == 'Overall'].sort_values('FIELD_RECORDS', ascending=False).head(15)

hdrs_st = ['State', 'Enriched Fan Records', '% of Overall Audience', '2019 %', '2021 %', '2022 %', '2023 %']
for c_i, h in enumerate(hdrs_st, 1):
    cell = ws_geo.cell(row=row_g, column=c_i)
    cell.value = h
    cell.font = font_tbl_header
    cell.fill = fill_navy
    cell.alignment = align_header
    cell.border = border_header
ws_geo.row_dimensions[row_g].height = 20
row_g += 1

for _, r_st in st_overall.iterrows():
    s_name = r_st['FIELD_VALUE']
    s_recs = r_st['FIELD_RECORDS']
    s_dist = r_st['FIELD_DISTRIBUTION']

    ws_geo.cell(row=row_g, column=1).value = str(s_name)
    ws_geo.cell(row=row_g, column=1).font = font_bold
    ws_geo.cell(row=row_g, column=1).alignment = align_left
    ws_geo.cell(row=row_g, column=1).border = border_cell

    ws_geo.cell(row=row_g, column=2).value = int(s_recs)
    ws_geo.cell(row=row_g, column=2).number_format = '#,##0'
    ws_geo.cell(row=row_g, column=2).font = font_bold
    ws_geo.cell(row=row_g, column=2).alignment = align_right
    ws_geo.cell(row=row_g, column=2).border = border_cell

    ws_geo.cell(row=row_g, column=3).value = float(s_dist)
    ws_geo.cell(row=row_g, column=3).number_format = '0.0%'
    ws_geo.cell(row=row_g, column=3).font = font_bold
    ws_geo.cell(row=row_g, column=3).alignment = align_right
    ws_geo.cell(row=row_g, column=3).fill = fill_light_blue
    ws_geo.cell(row=row_g, column=3).border = border_cell

    for c_i, yr_str in enumerate(['2019 Dell Technologies Match Play', '2021 Dell Technologies Match Play', '2022 Dell Technologies Match Play', '2023 Dell Technologies Match Play'], 4):
        yr_row = st_df[(st_df['FIELD_VALUE'] == s_name) & (st_df['SOURCE_TYPE'] == yr_str)]
        val = yr_row['FIELD_DISTRIBUTION'].values[0] if len(yr_row) > 0 else 0.0
        cell = ws_geo.cell(row=row_g, column=c_i)
        cell.value = float(val) if pd.notnull(val) else 0.0
        cell.number_format = '0.0%'
        cell.font = font_regular
        cell.alignment = align_right
        cell.border = border_cell

    ws_geo.row_dimensions[row_g].height = 19
    row_g += 1

# -------------------------------------------------------------------------
# TAB 4: RAW DISTRIBUTION DATA
# -------------------------------------------------------------------------
ws_raw = wb.create_sheet(title='Raw Distribution Data')
ws_raw.views.sheetView[0].showGridLines = True

headers_raw = list(df.columns)
for c_i, col_name in enumerate(headers_raw, 1):
    cell = ws_raw.cell(row=1, column=c_i)
    cell.value = col_name
    cell.font = font_tbl_header
    cell.fill = fill_navy
    cell.alignment = align_header
    cell.border = border_header
ws_raw.row_dimensions[1].height = 24

for r_i, r_data in enumerate(df.itertuples(index=False), 2):
    is_zebra = (r_i % 2 == 1)
    for c_i, val in enumerate(r_data, 1):
        cell = ws_raw.cell(row=r_i, column=c_i)
        cell.value = val
        cell.border = border_cell
        cell.font = font_regular

        if c_i in [4, 5]:
            cell.number_format = '#,##0'
            cell.alignment = align_right
        elif c_i == 6:
            cell.number_format = '0.00%'
            cell.alignment = align_right
        else:
            cell.alignment = align_left

        if is_zebra:
            cell.fill = fill_zebra
    ws_raw.row_dimensions[r_i].height = 18

for sheet in wb.worksheets:
    for col in sheet.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if cell.row in [1, 2] and sheet.title in ['Executive Overview', 'Demographic Distribution', 'Geographic Breakdown']:
                continue
            if '\n' in val_str:
                lines = val_str.split('\n')
                max_len = max(max_len, max(len(l) for l in lines))
            else:
                max_len = max(max_len, len(val_str))
        sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

ws_exec.column_dimensions['A'].width = 30
ws_exec.column_dimensions['B'].width = 14
ws_exec.column_dimensions['C'].width = 14
ws_exec.column_dimensions['D'].width = 14
ws_exec.column_dimensions['E'].width = 14
ws_exec.column_dimensions['F'].width = 14
ws_exec.column_dimensions['G'].width = 16
ws_exec.column_dimensions['H'].width = 16
ws_exec.column_dimensions['I'].width = 16

ws_demo.column_dimensions['A'].width = 34
for c_let in ['B', 'C', 'D', 'E', 'F', 'G']:
    ws_demo.column_dimensions[c_let].width = 16

ws_geo.column_dimensions['A'].width = 34
for c_let in ['B', 'C', 'D', 'E', 'F', 'G']:
    ws_geo.column_dimensions[c_let].width = 18

wb.save(excel_path)
print('Workbook successfully updated and saved to:', excel_path)

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference, Series

excel_path = 'WGC-DTMP Custom Enrichment Analysis/WGC_DTMP_Enrichment_Distribution.xlsx'
df = pd.read_excel(excel_path)
print('Data loaded successfully. Total rows:', len(df))

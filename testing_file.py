import chardet
import os
import pandas as pd

os.chdir
print(os.getcwd())
os.chdir('Finance Webapp')
print(os.getcwd())

with open('account-statement_2023-10-20_2025-04-21.csv', 'rb') as f:
    rawdata = f.read()
    result = chardet.detect(rawdata)
    print(rawdata[:100])
    print(result)

df = pd.read_excel('account-statement_2023-10-20_2025-04-21.csv')
print(df.head())
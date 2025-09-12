from pdfminer.high_level import extract_text
import pathlib
pdf = r"C:\Users\kedha\IT THESIS\290008_Brief_Treatment_Manual (002).pdf"
text = extract_text(pdf)
print(text[:2000])
out = pathlib.Path('content')/ 'manual_extracted.txt'
out.write_text(text, encoding='utf-8')
print("\nSaved to:", out)

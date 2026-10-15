from pypdf import PdfReader

reader = PdfReader("data/...")
print(f'共{len(reader.pages)}页')

page = reader.pages[0]
text = page.extract_text()
print(text[:500])
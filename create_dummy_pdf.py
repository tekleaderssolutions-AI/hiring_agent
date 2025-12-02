def create_pdf(filename):
    # Minimal PDF structure
    content = (
        b"%PDF-1.1\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 595 842] /Contents 4 0 R >>\n"
        b"endobj\n"
        b"4 0 obj\n"
        b"<< /Length 55 >>\n"
        b"stream\n"
        b"BT\n"
        b"/F1 24 Tf\n"
        b"100 700 Td\n"
        b"(Job Description: Software Engineer) Tj\n"
        b"ET\n"
        b"endstream\n"
        b"endobj\n"
        b"xref\n"
        b"0 5\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000060 00000 n \n"
        b"0000000117 00000 n \n"
        b"0000000274 00000 n \n"
        b"trailer\n"
        b"<< /Size 5 /Root 1 0 R >>\n"
        b"startxref\n"
        b"380\n"
        b"%%EOF\n"
    )
    with open(filename, "wb") as f:
        f.write(content)
    print(f"{filename} created")

if __name__ == "__main__":
    create_pdf("dummy_jd.pdf")

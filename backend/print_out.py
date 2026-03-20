with open("tmp_out.txt", "r", encoding="utf-16le", errors="ignore") as f:
    text = f.read()
    print(text[:2000].encode("ascii", "ignore").decode("ascii"))

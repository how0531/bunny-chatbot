
import re

def test_regex():
    # Mock data closely resembling the user's screenshot context
    raw_text = """
    • [【台積電法說會重點內容備忘錄】未來展望趨勢20251016] 閱讀進度
    0%
    閱讀進度
    法說會備忘錄
    台積電（市：2330）2025 年第三季營運表現強勁，營收與獲利均超出財測高標。
    預估今年首季美元營收346~358億美元，毛利率63~65%，營益率54~56%。
    台積電(2330)在最新的法說會中釋出震撼市場的強勁展望，預期2026年美元營收年增率將接近30%，並同步調升2026年資本支出至520億至560億美元之間。
    這項決策顯示公司對未來AI需求的掌握度極高。
    """

    print("--- Raw Text ---")
    print(raw_text)

    # Current Regex in SectorAnalyzer
    # Note: Added \n to the exclusion set to handle line breaks as delimiters
    financial_pattern = re.compile(r'([^。！？\n]*(?:營收|毛利|EPS|獲利|展望|成長|年增|季增|\d+%|\$\d+)[^。！？\n]*[。！？\n])')

    print("\n--- Matches ---")
    matches = financial_pattern.findall(raw_text)
    
    seen_sentences = set()
    count = 0 
    
    for sent in matches:
        clean_sent = sent.strip()
        # Clean up brackets
        clean_sent = re.sub(r'\[.*?\]', '', clean_sent)
        clean_sent = clean_sent.replace('• ', '')
        
        if len(clean_sent) > 10 and clean_sent not in seen_sentences:
            print(f"MATCH: {clean_sent}")
            seen_sentences.add(clean_sent)
            count += 1

    if count == 0:
        print("\n❌ NO MATCHES FOUND! (Would trigger fallback truncation)")

if __name__ == "__main__":
    test_regex()

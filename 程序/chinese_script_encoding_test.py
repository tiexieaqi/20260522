import tempfile
from pathlib import Path
from text_io import read_script_text

TEXT="《雨停之后》\n人物：林夏、陈默\n主要场景：旧书店门口\n关键道具：红色折叠伞\n"
def main():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)
        for name, enc in (("utf8.txt","utf-8"),("bom.txt","utf-8-sig"),("gb18030.txt","gb18030")):
            f=p/name; f.write_bytes(TEXT.encode(enc)); r=read_script_text(f); assert all(x in r["text"] for x in ("林夏","陈默","旧书店门口","红色折叠伞"))
        bad=p/'bad.txt'; bad.write_bytes(TEXT.replace("林夏","\ufffd").encode('utf-8')); 
        try: read_script_text(bad); raise AssertionError('corrupt accepted')
        except ValueError as e: assert 'script_text_corrupted' in str(e)
    print('chinese_script_encoding_test：全部通过')
if __name__=='__main__': main()

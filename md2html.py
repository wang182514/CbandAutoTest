"""Convert .md to .html for browser print-to-PDF (keeps exact markdown styling)."""
import sys, markdown

def md2html(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
    body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<style>
  body {{ font-family: 'Microsoft YaHei', sans-serif; font-size: 11pt;
         max-width: 780px; margin: 30px auto; padding: 0 20px; color: #222; line-height: 1.7; }}
  h1 {{ font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 6px; }}
  h2 {{ font-size: 14pt; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
  h3 {{ font-size: 12pt; }}
  table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
  th,td {{ border: 1px solid #999; padding: 5px 10px; text-align: center; }}
  th {{ background: #eee; }}
  pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; font-size: 9pt; white-space: pre-wrap; }}
  code {{ background: #f0f0f0; padding: 1px 4px; border-radius: 2px; }}
  blockquote {{ border-left: 3px solid #999; padding-left: 12px; color: #555; margin-left: 0; }}
</style></head><body>
{body}
</body></html>"""
    html_path = md_path.replace('.md', '.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Done → {html_path}  (用 Edge 打开后 Ctrl+P → 另存为 PDF)')

if __name__ == '__main__':
    md2html(sys.argv[1] if len(sys.argv) > 1 else '收发干扰手动测试.md')

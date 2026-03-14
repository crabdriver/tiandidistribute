import os
import requests
import markdown
import json
from bs4 import BeautifulSoup
import mimetypes
import time
import re
from dotenv import load_dotenv

# Load secret credentials from secrets.env
load_dotenv("secrets.env")

APPID = os.getenv("WECHAT_APPID")
SECRET = os.getenv("WECHAT_SECRET")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COVERS_DIR = os.path.join(BASE_DIR, "covers")

# 7 张独立的水墨国画风封面图，每篇文章一张
COVER_IMAGES = [
    os.path.join(COVERS_DIR, f"cover_0{i}.png") for i in range(1, 8)
]


class WeChatPublisher:
    def __init__(self, appid, secret):
        self.appid = appid
        self.secret = secret
        self.access_token = self.get_access_token()

    def get_access_token(self):
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.appid}&secret={self.secret}"
        response = requests.get(url).json()
        if 'access_token' in response:
            return response['access_token']
        elif response.get('errcode') == 40164:
            err_msg = response.get('errmsg', '')
            try:
                ip = err_msg.split('invalid ip ')[1].split(',')[0]
                print(f"\n[IP] 请将此IP加入白名单: {ip}")
            except:
                pass
            raise Exception(f"IP白名单未配置: {response}")
        else:
            raise Exception(f"获取Token失败: {response}")

    def upload_permanent_material(self, file_path, material_type="image"):
        """上传永久素材（封面图）"""
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={self.access_token}&type={material_type}"
        mime_type, _ = mimetypes.guess_type(file_path)
        with open(file_path, 'rb') as f:
            files = {'media': (os.path.basename(file_path), f, mime_type)}
            res = requests.post(url, files=files).json()
            if 'media_id' in res:
                return res['media_id'], res.get('url', '')
            else:
                raise Exception(f"上传封面失败: {res}")

    def upload_article_image(self, file_path_or_url, article_md_path):
        """上传文章正文内图片到微信图床"""
        url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={self.access_token}"
        file_content = None
        filename = "image.jpg"

        if file_path_or_url.startswith('http'):
            try:
                res = requests.get(file_path_or_url, timeout=15)
                if res.status_code == 200:
                    file_content = res.content
                    filename = os.path.basename(file_path_or_url.split('?')[0]) or "image.jpg"
            except Exception as e:
                print(f"  下载网络图片失败: {e}")
        else:
            local_path = file_path_or_url
            if not os.path.isabs(local_path):
                md_dir = os.path.dirname(os.path.abspath(article_md_path))
                local_path = os.path.normpath(os.path.join(md_dir, local_path))
            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    file_content = f.read()
                filename = os.path.basename(local_path)

        if not file_content:
            return None

        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "image/jpeg"
        files = {'media': (filename, file_content, mime_type)}
        upload_res = requests.post(url, files=files).json()
        return upload_res.get('url')

    def md_to_wechat_html(self, md_text, md_file_path, top_image_url=None):
        """
        精确复刻截图中的极简国风排版样式：
        - 米色暖底 (#faf9f5)
        - 标题粗体左对齐、正文深灰舒适行距
        - 二级标题只加粗，无花哨装饰
        - 全宽顶部头图
        """
        # 清理开头重复的 H1 标题和失效的本地 Markdown 配图（解决红框问题）
        lines = md_text.split('\n')
        start_idx = 0
        for i, line in enumerate(lines):
            s = line.strip()
            if s == '' or s.startswith('# ') or s.startswith('!['):
                continue
            else:
                start_idx = i
                break
        clean_md_text = '\n'.join(lines[start_idx:])

        # 去掉 nl2br，它会导致微信列表解析出多余空行
        raw_html = markdown.markdown(clean_md_text, extensions=['extra', 'codehilite'])
        soup = BeautifulSoup(raw_html, 'html.parser')

        # 解决微信列表排版 BUG：如果 li 内嵌了 p，微信会产生多余的断行和空白序号
        for li in soup.find_all('li'):
            for p in li.find_all('p'):
                p.unwrap()

        # 处理文章内部图片 -> 上传微信图床
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                wechat_img_url = self.upload_article_image(src, md_file_path)
                if wechat_img_url:
                    img['src'] = wechat_img_url
                    img['data-src'] = wechat_img_url
                img['style'] = 'display: block; max-width: 100%; height: auto; margin: 20px auto;'

        # ========= 精确复刻截图的样式 =========
        # H1: 大标题，粗体，深色，左对齐
        for tag in soup.find_all('h1'):
            tag['style'] = (
                'font-size: 22px; font-weight: bold; color: #1a1a1a; '
                'margin-top: 15px; margin-bottom: 8px; line-height: 1.4; '
                'text-align: left; letter-spacing: 0.5px;'
            )

        # H2: 粗体左对齐，无背景色无边框，仅加粗
        for tag in soup.find_all('h2'):
            tag['style'] = (
                'font-size: 18px; font-weight: bold; color: #1a1a1a; '
                'margin-top: 20px; margin-bottom: 8px; line-height: 1.4;'
            )

        # H3: 稍小，粗黑
        for tag in soup.find_all('h3'):
            tag['style'] = (
                'font-size: 16px; font-weight: bold; color: #333333; '
                'margin-top: 22px; margin-bottom: 10px;'
            )

        # P: 正文段落
        for tag in soup.find_all('p'):
            tag['style'] = (
                'font-size: 15px; color: #3f3f3f; line-height: 1.8; '
                'margin-bottom: 12px; letter-spacing: 0.5px; text-align: justify;'
            )

        # Blockquote: 简洁引用
        for tag in soup.find_all('blockquote'):
            tag['style'] = (
                'border-left: 3px solid #c0c0c0; padding: 10px 16px; '
                'color: #666666; background-color: #f5f5f0; '
                'margin: 18px 0; font-size: 14px; border-radius: 0 4px 4px 0;'
            )

        # UL/OL
        for tag in soup.find_all(['ul', 'ol']):
            tag['style'] = (
                'margin-bottom: 18px; padding-left: 22px; '
                'color: #3f3f3f; font-size: 15px; line-height: 1.8;'
            )

        # LI
        for tag in soup.find_all('li'):
            tag['style'] = 'margin-bottom: 6px;'

        # Strong: 只加粗，颜色略深
        for tag in soup.find_all('strong'):
            tag['style'] = 'color: #1a1a1a; font-weight: bold;'

        # Em
        for tag in soup.find_all('em'):
            tag['style'] = 'color: #888888; font-style: italic;'

        # A
        for tag in soup.find_all('a'):
            tag['style'] = 'color: #576b95; text-decoration: none;'

        # 顶部全宽头图
        top_banner_html = ""
        if top_image_url:
            top_banner_html = (
                f'<img src="{top_image_url}" data-src="{top_image_url}" '
                f'style="display: block; width: 100%; height: auto; margin: 0 0 15px 0;" />'
            )

        # 整体容器：米色暖底，极简留白
        wechat_html = f"""<section style="margin: 0; padding: 15px 16px 20px 16px; background-color: #faf9f5; overflow-wrap: break-word; font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;">
{top_banner_html}
{str(soup)}
</section>"""
        return wechat_html

    def publish_draft(self, title, md_content, md_file_path, cover_media_id, cover_url=None):
        html_content = self.md_to_wechat_html(md_content, md_file_path, top_image_url=cover_url)
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={self.access_token}"

        digest_soup = BeautifulSoup(markdown.markdown(md_content), 'html.parser')
        abstract = digest_soup.get_text()[:54].replace('\n', ' ').strip()

        payload = {
            "articles": [
                {
                    "title": title,
                    "author": "川上行远",
                    "digest": abstract + "...",
                    "content": html_content,
                    "thumb_media_id": cover_media_id,
                    "need_open_comment": 1,
                    "only_fans_can_comment": 0
                }
            ]
        }
        res = requests.post(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        return res.json()


def main():
    try:
        print("=" * 50)
        print("  微信公众号自动发布引擎 v3.0")
        print("  公众号: 川上行远")
        print("=" * 50)

        publisher = WeChatPublisher(APPID, SECRET)
        print("[OK] Token 获取成功\n")

        target_dir = r"D:\tiandiworkspace\拆解后文章"
        files = sorted([f for f in os.listdir(target_dir) if f.endswith('.md')])

        if not files:
            print("没有找到 markdown 文章！")
            return

        num_to_publish = min(7, len(files))
        print(f"找到 {len(files)} 篇文章，准备发布前 {num_to_publish} 篇\n")

        for idx in range(num_to_publish):
            target_file = files[idx]
            raw_title = os.path.splitext(target_file)[0]
            title = re.sub(r'^[0-9-]*_', '', raw_title) # 去除前面的 11-06_ 等序号前缀
            
            md_file_path = os.path.join(target_dir, target_file)

            # 每篇文章使用不同的封面图
            cover_path = COVER_IMAGES[idx % len(COVER_IMAGES)]
            cover_name = os.path.basename(cover_path)

            print(f"--- [{idx+1}/{num_to_publish}] {title} ---")
            print(f"  封面: {cover_name}")

            # 上传该篇文章的独立封面
            cover_media_id, cover_url = publisher.upload_permanent_material(cover_path)
            print(f"  封面上传成功")

            with open(md_file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            result = publisher.publish_draft(title, md_content, md_file_path, cover_media_id, cover_url=cover_url)

            if result.get('errcode') == 0 or 'media_id' in result:
                print(f"  [OK] 草稿发布成功: {result.get('media_id')}")
            else:
                print(f"  [FAIL] {result}")

            # 间隔避免限流
            if idx < num_to_publish - 1:
                time.sleep(2)

        print(f"\n{'=' * 50}")
        print(f"  全部 {num_to_publish} 篇文章处理完毕！")
        print(f"  请前往公众号后台草稿箱查看效果")
        print(f"{'=' * 50}")

    except Exception as e:
        print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    main()

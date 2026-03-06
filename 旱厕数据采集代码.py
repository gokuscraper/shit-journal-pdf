#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Auther  : 爬虫孙大圣 v:pachong7
# @Time    : 2026/3/6 12:23

import os
import requests
import json
import re
import time

# --- 配置信息 ---
BASE_URL = "https://bcgdqepzakcufaadgnda.supabase.co"
REST_URL = f"{BASE_URL}/rest/v1/preprints_with_ratings_mat"
STORAGE_SIGN_URL = f"{BASE_URL}/storage/v1/object/sign/manuscripts"
STORAGE_BASE_URL = f"{BASE_URL}/storage/v1"

HEADERS = {
    "apikey": "sb_publishable_wHqWLjQwO2lMwkGLeBktng_Mk_xf5xd",
    "authorization": "Bearer sb_publishable_wHqWLjQwO2lMwkGLeBktng_Mk_xf5xd",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "referer": "https://shitjournal.org/",
    "content-type": "application/json"
}

ROOT_DIR = "旱厕"


def clean_filename(filename):
    """
    稳健的文件名清洗：
    1. 替换Windows非法字符
    2. 彻底去除末尾的空格和点
    3. 限制长度防止路径过长
    """
    # 替换非法字符
    name = re.sub(r'[\\/:*?"<>|]', '_', filename)
    # 替换换行符等控制字符
    name = re.sub(r'\s+', ' ', name)
    # 去除两端空格，并去除末尾的点
    name = name.strip().rstrip('.')
    # 限制文件夹名长度（取前80个字符，留够余量给路径）
    return name[:80].strip()


def download_file(url, save_path):
    """流式下载文件，带重试机制"""
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"      [!] 下载出错: {e}")
        return False


def main():
    # 1. 初始化目录
    if not os.path.exists(ROOT_DIR):
        os.makedirs(ROOT_DIR)
        print(f"[*] 已创建根目录: {ROOT_DIR}")

    # 2. 获取全部列表
    print("[*] 正在从服务器拉取全部论文清单...")
    params = {
        "select": "id,manuscript_title,author_name,institution,viscosity,discipline,created_at,avg_score,rating_count,weighted_score,co_authors,pdf_path",
        "zone": "eq.latrine",
        "order": "latrine_recency.asc",
        "limit": 1000  # 设置为1000以覆盖全部807篇
    }

    try:
        response = requests.get(REST_URL, headers=HEADERS, params=params)
        response.raise_for_status()
        articles = response.json()
        total = len(articles)
        print(f"[+] 发现 {total} 篇论文，准备开始下载...\n")
    except Exception as e:
        print(f"[-] 获取列表失败，请检查网络: {e}")
        return

    # 3. 开始遍历
    for index, item in enumerate(articles, 1):
        raw_title = item.get('manuscript_title') or "Untitled"
        author = item.get('author_name', '匿名')
        pdf_path_raw = item.get('pdf_path')

        # 生成安全文件夹名
        safe_title = clean_filename(f"{index:03d}_{raw_title}")
        article_dir = os.path.join(ROOT_DIR, safe_title)

        print(f"--- [{index}/{total}] 处理中: {raw_title[:40]}... ---")

        # 创建文件夹
        if not os.path.exists(article_dir):
            os.makedirs(article_dir)



        # B. 处理 PDF
        save_pdf_path = os.path.join(article_dir, "manuscript.pdf")

        # 检查是否已经下载过
        if os.path.exists(save_pdf_path) and os.path.getsize(save_pdf_path) > 1000:
            print(f"   [~] PDF 已存在，跳过下载")
            continue

        if pdf_path_raw:
            try:
                # 1. 申请签名链接
                sign_url = f"{STORAGE_SIGN_URL}/{pdf_path_raw}"
                sign_res = requests.post(sign_url, headers=HEADERS, json={"expiresIn": 3600}, timeout=20)

                if sign_res.status_code == 200:
                    signed_url_suffix = sign_res.json().get('signedURL')
                    full_download_url = f"{STORAGE_BASE_URL}{signed_url_suffix}"

                    # 2. 执行下载
                    print(f"   [>] 正在下载 PDF...")
                    if download_file(full_download_url, save_pdf_path):
                        print(f"   [+] 下载成功")
                    else:
                        print(f"   [!] 下载过程出错")
                else:
                    print(f"   [!] 鉴权失败，状态码: {sign_res.status_code}")
            except Exception as e:
                print(f"   [!] 获取链接异常: {e}")
        else:
            print(f"   [!] 数据库中无 PDF 路径")


        time.sleep(5)

    print("\n" + "=" * 50)
    print(f"全部任务处理完毕！共计处理 {total} 个文件夹。")
    print("=" * 50)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import urllib.request
from bs4 import BeautifulSoup
import numpy as np
import datetime

dt_now = datetime.datetime.now()
dt = dt_now.strftime('%d')
day = str(dt)
month = str(dt_now.month)

def extract_page_url(infomation_url):
    req = urllib.request.Request(infomation_url)
    html = urllib.request.urlopen(req)
    soup = BeautifulSoup(html, "html.parser")

    topic = soup.find_all('div', attrs={'class': 'm-grid__col1'})[1]
    article_urls = [tag['href'] for tag in topic.find_all('a', href=True)]
    article_titles = [tag.text for tag in topic.find_all('a', href=True)]
    return article_urls, article_titles

target_url = "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000121431_00086.html"
page_urls, page_titles = extract_page_url(target_url)

def get_pdf_url(target_url):
        req = urllib.request.Request(target_url)
        html = urllib.request.urlopen(req)
        soup = BeautifulSoup(html, "html.parser")
        for atag in soup.find_all('a', href=True):
            if '各都道府県の検査陽性者の状況' in atag.text:
                return atag['href']         

pdf_url = "https://www.mhlw.go.jp" + get_pdf_url(page_urls[0])

# PDF内の表をローカルにダウンロード   
pdf_file_name = "infected_person_data_" + month + "_" + day + ".pdf"
urllib.request.urlretrieve(pdf_url, pdf_file_name)


# PDF内の表をpandasフレームに変換する
# import pandas as pd
import tabula
df = tabula.read_pdf(pdf_file_name, pages = '1', multiple_tables = False)[0]

# Unnamed: 9がない場合、Unnamed; 8だけを消去
try:
    df = df.drop(["Unnamed: 8", "Unnamed: 9"], axis=1)
except:
    df = df.drop(["Unnamed: 8"], axis=1)
else:
    print("Error")
    
    
# データフレームのリネーム
df = df.rename(columns={"Unnamed: 0": "都道府県名", 
                        "Unnamed: 1": "陽性者数",
                        "Unnamed: 2": "PCR検査実施人数",
                        "入院治療等を": "入院治療等を要する者（人）",
                        "Unnamed: 4": "うち重症",
                        "退院又は療養解除": "退院又は療養解除となった者の数（人）",
                        "Unnamed: 6": "死亡（累積）（人）",
                        "Unnamed: 7": "確認中（人）"})

# 邪魔な文字を置換で消去
df["都道府県名"] = df["都道府県名"].str.replace('※4', '')
df["都道府県名"] = df["都道府県名"].str.replace('※5', '')
df["都道府県名"] = df["都道府県名"].str.replace('※7', '')
df["都道府県名"] = df["都道府県名"].str.replace(' ', '')	
df["陽性者数"] = df["陽性者数"].str.replace(',', '')	
df = df.fillna(0)
df = df.drop(df.index[[0, 1, len(df)-1, len(df)-2]])
df.reset_index(drop=True)
df.index = np.arange(1, len(df) + 1)


# Flaskサーバの立ち上げ
from flask import Flask
from flask import Response
import os
app = Flask(__name__)

@app.route("/")
# Flaskサーバにdataframeをjsonで出力
def infected_person():
    return Response(df.to_json(orient="records"), mimetype='application/json')

if __name__ == "__main__":
    app.run(host=os.getenv('APP_ADDRESS', 'localhost'), port=8000)
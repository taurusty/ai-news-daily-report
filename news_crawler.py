#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import time
import datetime
import requests
import random
from bs4 import BeautifulSoup
import jieba.analyse
import schedule
import nltk
import json
import re
from urllib.parse import quote, urljoin

# 确保nltk数据包已下载
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# 定义请求头列表，避免被反爬
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
]

# 定义保存日报的目录
DATA_DIR = "daily_reports"
os.makedirs(DATA_DIR, exist_ok=True)

# 定义超时设置，避免爬虫卡住
TIMEOUT = 10

# Server酱配置 (需要自行注册Server酱并设置SCKEY)
# 获取方式：登录 https://sct.ftqq.com/ 获取
SERVERCHAN_SEND_KEY = ""  # 在这里填入您的SendKey

class NewsItem:
    def __init__(self, title, url, source, date, summary=None, heat_score=0):
        self.title = title
        self.url = url
        self.source = source
        self.date = date
        self.summary = summary
        self.heat_score = heat_score
    
    def __str__(self):
        return f"{self.title} - {self.source} - {self.date}"

def get_random_headers():
    """获取随机请求头，避免被反爬"""
    return {"User-Agent": random.choice(USER_AGENTS)}

def fetch_baidu_news():
    """从百度新闻获取大模型相关新闻"""
    news_items = []
    
    try:
        url = "https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&word=大模型"
        response = requests.get(url, headers=get_random_headers(), timeout=TIMEOUT)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"百度新闻请求失败: {response.status_code}")
            return news_items
        
        soup = BeautifulSoup(response.text, 'html.parser')
        news_divs = soup.select(".result")  # 修改选择器，适应百度搜索结果的实际CSS类名
        
        if not news_divs:
            news_divs = soup.select(".result-op")  # 尝试备选选择器
        
        if not news_divs:
            print("无法找到新闻内容，可能需要更新CSS选择器")
            return news_items
            
        for div in news_divs:
            try:
                title_elem = div.select_one("h3 a") or div.select_one("a.news-title")
                if not title_elem:
                    continue
                
                title = title_elem.get_text().strip()
                news_url = title_elem.get("href", "")
                
                source_time = ""
                source_elem = div.select_one(".c-author") or div.select_one(".news-source")
                if source_elem:
                    source_time = source_elem.get_text().strip()
                
                parts = source_time.split("  ")
                source = parts[0] if parts else "百度新闻"
                # 清理来源字段中可能的多余字符
                source = source.strip().rstrip(',')
                date_str = parts[1] if len(parts) > 1 else "今天"
                
                # 获取摘要 - 尝试多种选择器
                summary = None
                summary_selectors = [
                    ".c-summary", ".news-summary", ".content-right_8Zs40",
                    ".c-span-last", ".c-color-text", "p", ".c-gap-top-small"
                ]
                
                for selector in summary_selectors:
                    summary_elem = div.select_one(selector)
                    if summary_elem:
                        summary_text = summary_elem.get_text(strip=True)
                        if summary_text and len(summary_text) > 20:  # 确保摘要有足够的长度
                            summary = summary_text
                            break
                
                # 如果还是没有找到摘要，尝试获取div内的所有文本
                if not summary:
                    # 移除标题和来源元素
                    content_div = div.copy()
                    for elem in content_div.select("h3, .c-author, .news-source"):
                        if elem:
                            elem.decompose()
                    
                    # 获取剩余文本作为摘要
                    div_text = content_div.get_text(strip=True)
                    if div_text and len(div_text) > 20:
                        summary = div_text
                
                # 如果还是没有摘要，使用标题作为默认摘要
                if not summary:
                    summary = f"关于'{title}'的新闻"
                
                # 计算热度分数 (这里使用简单的评估方法，可以根据需要改进)
                heat_score = 0
                if "今天" in date_str:
                    heat_score += 50
                elif "小时" in date_str:
                    heat_score += 30
                elif "分钟" in date_str:
                    heat_score += 40
                else:
                    heat_score += 10
                    
                # 添加标题权重
                keywords = ["ChatGPT", "GPT", "大模型", "人工智能", "AI", "大语言模型", "LLM"]
                for keyword in keywords:
                    if keyword in title:
                        heat_score += 20
                
                news_items.append(NewsItem(
                    title=title,
                    url=news_url,
                    source=source,
                    date=date_str,
                    summary=summary,
                    heat_score=heat_score
                ))
            except Exception as e:
                print(f"解析新闻项出错: {e}")
    except Exception as e:
        print(f"获取百度新闻时发生错误: {e}")
    
    return news_items

def fetch_sina_news():
    """从新浪新闻获取大模型相关新闻"""
    news_items = []
    
    try:
        url = "https://search.sina.com.cn/?q=大模型&c=news"
        response = requests.get(url, headers=get_random_headers(), timeout=TIMEOUT)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"新浪新闻请求失败: {response.status_code}")
            return news_items
        
        soup = BeautifulSoup(response.text, 'html.parser')
        news_divs = soup.select(".box-result")
        
        for div in news_divs:
            try:
                title_elem = div.select_one("h2 a")
                if not title_elem:
                    continue
                
                title = title_elem.get_text().strip()
                news_url = title_elem.get("href", "")
                
                source_elem = div.select_one(".fgray_time")
                source_text = source_elem.get_text().strip() if source_elem else ""
                source = source_text.split()[0] if source_text and source_text.split() else "新浪"
                # 清理来源字段中可能的多余字符
                source = source.strip().rstrip(',')
                date_str = source_text.split()[1] if source_text and len(source_text.split()) > 1 else "今天"
                
                # 获取摘要
                summary = None
                summary_elem = div.select_one(".content")
                if summary_elem:
                    summary = summary_elem.get_text().strip()
                
                # 如果没有摘要，使用标题作为默认摘要
                if not summary or len(summary) < 20:
                    summary = f"关于'{title}'的新闻"
                
                # 计算热度分数
                heat_score = 0
                if "今天" in date_str:
                    heat_score += 50
                elif "小时" in date_str:
                    heat_score += 30
                elif "分钟" in date_str:
                    heat_score += 40
                else:
                    heat_score += 10
                    
                # 添加标题权重
                keywords = ["ChatGPT", "GPT", "大模型", "人工智能", "AI", "大语言模型", "LLM"]
                for keyword in keywords:
                    if keyword in title:
                        heat_score += 20
                
                news_items.append(NewsItem(
                    title=title,
                    url=news_url,
                    source=source,
                    date=date_str,
                    summary=summary,
                    heat_score=heat_score
                ))
            except Exception as e:
                print(f"解析新浪新闻项出错: {e}")
    except Exception as e:
        print(f"获取新浪新闻时发生错误: {e}")
    
    return news_items

def get_article_summary(url):
    """使用BeautifulSoup直接从文章页面提取内容"""
    try:
        # 如果是百度新闻链接，需要特殊处理
        if "baijiahao.baidu.com" in url or "mbd.baidu.com" in url:
            return extract_baidu_article_summary(url)
            
        response = requests.get(url, headers=get_random_headers(), timeout=TIMEOUT)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"获取文章内容失败: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尝试多种选择器来获取文章内容
        content_selectors = [
            "article", ".article-content", ".article_content", 
            ".content", "#content", ".news-content", ".detail-content",
            ".main-content", ".post-content", ".entry-content"
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除脚本和样式
                for script in content_elem(["script", "style"]):
                    script.decompose()
                
                # 获取文本内容
                text = content_elem.get_text(strip=True)
                # 简单处理，取前200个字符作为摘要
                if text and len(text) > 200:
                    return text[:200] + "..."
                elif text:
                    return text
        
        # 如果上述选择器都没有找到内容，尝试获取所有p标签
        paragraphs = soup.select("p")
        if paragraphs:
            text = " ".join([p.get_text(strip=True) for p in paragraphs[:5]])
            if text and len(text) > 200:
                return text[:200] + "..."
            elif text:
                return text
                
        return "无法获取文章摘要"
    except Exception as e:
        print(f"获取文章摘要失败: {e}")
        return "获取摘要时出错"

def extract_baidu_article_summary(url):
    """专门用于从百度文章提取摘要"""
    try:
        response = requests.get(url, headers=get_random_headers(), timeout=TIMEOUT)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"获取百度文章内容失败: {response.status_code}")
            return "无法获取百度文章内容"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 百度文章内容选择器
        baidu_selectors = [
            ".article-content", "#article_content", ".article",
            ".mainContent", "#main_content", ".content-wrapper",
            "[class*=article]", "[class*=content]"
        ]
        
        # 尝试所有可能的选择器
        for selector in baidu_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除无用元素
                for unwanted in content_elem.select(".author-info, .article-source, .article-tag, script, style"):
                    if unwanted:
                        unwanted.decompose()
                
                # 获取所有段落
                paragraphs = content_elem.select("p")
                if paragraphs:
                    # 取前3个非空段落组成摘要
                    text_parts = []
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
                        if p_text and len(p_text) > 10:  # 忽略太短的段落
                            text_parts.append(p_text)
                            if len(text_parts) >= 3:
                                break
                    
                    if text_parts:
                        summary = " ".join(text_parts)
                        if len(summary) > 200:
                            return summary[:200] + "..."
                        return summary
                
                # 如果没有找到段落，获取整个文本
                text = content_elem.get_text(strip=True)
                if text:
                    if len(text) > 200:
                        return text[:200] + "..."
                    return text
        
        # 尝试直接获取所有段落
        all_paragraphs = soup.select("p")
        if all_paragraphs:
            text_parts = []
            for p in all_paragraphs:
                p_text = p.get_text(strip=True)
                if p_text and len(p_text) > 15:  # 忽略太短的段落
                    text_parts.append(p_text)
                    if len(text_parts) >= 3:
                        break
            
            if text_parts:
                summary = " ".join(text_parts)
                if len(summary) > 200:
                    return summary[:200] + "..."
                return summary
        
        # 如果都没有找到，返回默认值
        return "未能从百度文章中提取到摘要"
    
    except Exception as e:
        print(f"提取百度文章摘要时出错: {e}")
        return "提取百度文章摘要时出错"

def extract_keywords(text, top_n=5):
    """从文本中提取关键词"""
    if not text:
        return []
    return jieba.analyse.textrank(text, topK=top_n)

def fetch_wechat_news():
    """从搜狗微信搜索获取大模型相关新闻"""
    print("正在从搜狗微信获取公众号文章...")
    news_items = []
    
    # 搜索关键词列表
    keywords = ["大模型", "ChatGPT", "GPT", "人工智能 大模型", "LLM"]
    
    for keyword in keywords:
        try:
            url = "https://weixin.sogou.com/weixin"
            params = {
                "type": 2,  # 搜索类型，2表示文章
                "query": keyword,  # 搜索关键词
                "ie": "utf8",
                "s_from": "input",
                "from": "input",
                "_sug_": "n",
                "_sug_type_": ""
            }
            
            headers = get_random_headers()
            # 添加一些额外的请求头，使请求更像浏览器发出的
            headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            })
            
            response = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"搜狗微信搜索请求失败: {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查是否有验证码
            if "验证码" in response.text or "请输入验证码" in response.text:
                print("搜狗微信搜索需要验证码，请稍后再试或使用代理IP")
                continue
            
            # 尝试多个可能的选择器
            articles = soup.select(".news-box .news-list li")
            
            if not articles:
                articles = soup.select("ul.news-list li")
            
            if not articles:
                print(f"未找到微信公众号文章，可能需要更新选择器。关键词: {keyword}")
                continue
                
            print(f"找到 {len(articles)} 篇与 '{keyword}' 相关的微信公众号文章")
            
            for article in articles:
                try:
                    # 尝试提取标题和链接
                    title_elem = article.select_one("h3 a") or article.select_one("h4 a")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    article_url = title_elem.get("href", "")
                    
                    # 完整的URL可能需要拼接
                    if article_url.startswith('/'):
                        article_url = urljoin("https://weixin.sogou.com", article_url)
                    
                    # 提取公众号名称（来源）
                    source_elem = article.select_one(".account") or article.select_one(".s-p")
                    source = "未知公众号"
                    if source_elem:
                        source = source_elem.get_text(strip=True)
                    
                    # 提取发布时间
                    time_elem = article.select_one(".s2 span") or article.select_one(".s2")
                    pub_time = "今天"
                    if time_elem:
                        pub_time_text = time_elem.get_text(strip=True)
                        if pub_time_text:
                            pub_time = pub_time_text
                    
                    # 提取文章摘要
                    summary_elem = article.select_one(".txt-info") or article.select_one(".txt_info")
                    summary = ""
                    if summary_elem:
                        summary = summary_elem.get_text(strip=True)
                    
                    # 如果摘要为空，尝试获取整个内容区域的文本
                    if not summary:
                        # 复制article元素，移除标题和来源元素
                        content_article = article.copy()
                        for elem in content_article.select("h3, h4, .account, .s-p, .s2"):
                            if elem:
                                elem.decompose()
                        
                        summary = content_article.get_text(strip=True)
                    
                    # 计算热度分数
                    heat_score = calculate_wechat_heat(source, title, pub_time, keyword)
                    
                    # 创建新闻条目
                    news_item = NewsItem(
                        title=title,
                        url=article_url,
                        source=source,
                        date=datetime.datetime.now().strftime("%Y-%m-%d"),
                        summary=summary,
                        heat_score=heat_score
                    )
                    
                    news_items.append(news_item)
                    
                except Exception as e:
                    print(f"处理微信公众号文章时出错: {e}")
            
            # 每个关键词搜索后休眠，避免频繁请求
            time.sleep(random.uniform(3, 5))
            
        except Exception as e:
            print(f"获取微信公众号文章时发生错误: {e}")
    
    print(f"总共获取了 {len(news_items)} 条微信公众号文章")
    return news_items

def calculate_wechat_heat(account_name, title, pub_time, keyword):
    """计算微信公众号文章热度"""
    base_score = 40  # 基础分数
    
    # 知名公众号名单及其权重
    famous_accounts = {
        "腾讯AI实验室": 30,
        "腾讯研究院": 30,
        "百度AI": 30,
        "智源研究院": 25,
        "AI科技评论": 25,
        "机器之心": 25,
        "量子位": 25,
        "新智元": 25,
        "人工智能学家": 20,
        "AIGC": 20,
        "专知": 20,
        "AI前线": 20,
        "AI新媒体联盟": 20,
        "中国人工智能学会": 20,
    }
    
    # 根据公众号名称加分
    for account, score in famous_accounts.items():
        if account in account_name:
            base_score += score
            break
    else:
        # 如果不在知名列表中，但有一些关键词，也加分
        media_keywords = ["AI", "人工智能", "科技", "技术", "学院", "研究", "实验室"]
        for media_keyword in media_keywords:
            if media_keyword in account_name:
                base_score += 10
                break
    
    # 标题权重
    title_keywords = {
        "大模型": 15,
        "GPT-4": 15,
        "GPT4": 15,
        "ChatGPT": 15,
        "LLM": 10,
        "AIGC": 10,
        "人工智能": 5,
        "AI": 5,
        "模型": 5,
        "Transformer": 10,
        "自然语言处理": 5,
        "NLP": 5,
        "机器学习": 5,
        "深度学习": 5,
    }
    
    # 根据标题关键词加分
    for title_keyword, score in title_keywords.items():
        if title_keyword in title:
            base_score += score
    
    # 搜索关键词权重 - 精确匹配的关键词分数更高
    if keyword in title:
        base_score += 15
    
    # 时间权重
    if "今天" in pub_time:
        base_score += 20
    elif "小时" in pub_time:
        # 提取小时数
        hour_match = re.search(r'(\d+)小时', pub_time)
        if hour_match:
            hours = int(hour_match.group(1))
            if hours <= 6:
                base_score += 15
            else:
                base_score += 10
    elif "分钟" in pub_time:
        base_score += 20
    elif "昨天" in pub_time:
        base_score += 5
    
    return base_score

def extract_wechat_article_summary(url):
    """从微信文章页面提取摘要"""
    try:
        headers = get_random_headers()
        # 添加一些额外的请求头，使请求更像浏览器发出的
        headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"获取微信文章内容失败: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 微信文章内容选择器
        content_selectors = [
            "#js_content",  # 标准微信文章内容区
            ".rich_media_content",  # 另一个常见内容区类名
            "div.rich_media_area_primary",  # 主要内容区
            "div.rich_media_area_primary_inner",  # 内容区的内部容器
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除所有脚本和样式标签
                for script in content_elem(["script", "style"]):
                    script.decompose()
                
                # 获取段落
                paragraphs = content_elem.select("p")
                if paragraphs:
                    # 提取前3个非空段落作为摘要
                    text_parts = []
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
                        if p_text and len(p_text) > 10:  # 忽略太短的段落
                            text_parts.append(p_text)
                            if len(text_parts) >= 3:
                                break
                    
                    if text_parts:
                        summary = " ".join(text_parts)
                        if len(summary) > 200:
                            return summary[:200] + "..."
                        return summary
                
                # 如果没有找到段落，获取整个文本
                text = content_elem.get_text(strip=True)
                if text:
                    if len(text) > 200:
                        return text[:200] + "..."
                    return text
        
        return "无法提取微信文章摘要"
    
    except Exception as e:
        print(f"提取微信文章摘要时出错: {e}")
        return "提取微信文章摘要时出错"

def generate_daily_report():
    """生成每日日报并保存为CSV"""
    print("开始生成每日大模型新闻日报...")
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(DATA_DIR, f"大模型日报_{today}.csv")
    
    # 只从微信公众号获取新闻
    news_items = []
    news_items.extend(fetch_wechat_news())
    
    if not news_items:
        print("未获取到任何微信公众号文章，请检查网络连接或更新选择器")
        return None
    
    # 去重 (基于URL和标题)
    unique_urls = set()
    unique_titles = set()
    unique_news = []
    
    for item in news_items:
        # 使用URL和标题的组合进行去重
        if item.url not in unique_urls and item.title not in unique_titles and item.url:
            unique_urls.add(item.url)
            unique_titles.add(item.title)
            unique_news.append(item)
    
    print(f"去重后剩余 {len(unique_news)} 条微信公众号文章")
    
    # 按热度分数排序
    sorted_news = sorted(unique_news, key=lambda x: x.heat_score, reverse=True)
    
    # 只保留前10条新闻
    top_news = sorted_news[:10] if len(sorted_news) > 10 else sorted_news
    
    # 获取详细摘要（如果原来没有或摘要太短）
    for i, item in enumerate(top_news):
        print(f"正在处理第 {i+1}/{len(top_news)} 条新闻: {item.title[:20]}...")
        
        # 如果摘要为空或者长度不足，尝试获取更详细的摘要
        if not item.summary or len(item.summary) < 30:
            try:
                # 使用专门的函数提取微信文章摘要
                new_summary = extract_wechat_article_summary(item.url)
                if new_summary and new_summary not in ["无法提取微信文章摘要", "提取微信文章摘要时出错"]:
                    item.summary = new_summary
                    print(f"  成功获取微信文章摘要")
                else:
                    print(f"  无法获取微信文章摘要，保留原摘要")
            except Exception as e:
                print(f"  处理摘要时发生错误: {e}")
        else:
            print(f"  已有足够长度的摘要，跳过")
        
        # 休眠一下，避免请求过快
        time.sleep(random.uniform(1, 3))
    
    # 保存为CSV
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['日期', '标题', '内容摘要', '信息来源', 'URL', '热度分数'])
            
            for item in top_news:
                # 处理摘要中可能包含的逗号、换行符等，避免CSV格式错误
                summary = item.summary if item.summary else "无摘要"
                # 移除摘要中的换行符
                summary = summary.replace('\n', ' ').replace('\r', ' ')
                
                # 确保信息来源字段没有多余的逗号
                source = item.source.strip().rstrip(',') if item.source else "未知公众号"
                
                writer.writerow([
                    today,
                    item.title,
                    summary,
                    source,
                    item.url,
                    item.heat_score
                ])
        
        print(f"日报已保存到 {filename}")
        
        # 将日报推送到微信
        push_to_wechat(top_news, today)
        
        return filename
    except Exception as e:
        print(f"保存CSV文件时出错: {e}")
        return None

def push_to_wechat(news_items, date):
    """将日报推送到微信"""
    if not SERVERCHAN_SEND_KEY:
        print("未配置Server酱SendKey，跳过微信推送")
        return False
    
    try:
        # 构建微信推送内容
        title = f"大模型日报 - {date}"
        
        # 构建正文内容，使用Markdown格式
        desp = f"# 今日大模型热点新闻 ({date})\n\n"
        
        for i, item in enumerate(news_items):
            # 清理摘要文本
            summary = item.summary if item.summary else "无摘要"
            if len(summary) > 100:
                summary = summary[:100] + "..."
            
            # 添加新闻条目，使用Markdown格式
            desp += f"### {i+1}. {item.title}\n"
            desp += f"**来源**: {item.source}  **热度**: {item.heat_score}\n\n"
            desp += f"{summary}\n\n"
            desp += f"[阅读原文]({item.url})\n\n"
            desp += "---\n\n"
        
        # 添加日报生成时间脚注
        desp += f"\n\n*日报生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        # 发送到Server酱
        send_url = f"https://sctapi.ftqq.com/{SERVERCHAN_SEND_KEY}.send"
        data = {
            "title": title,
            "desp": desp
        }
        
        response = requests.post(send_url, data=data, timeout=TIMEOUT)
        result = response.json()
        
        if result.get("code") == 0:
            print("微信推送成功！")
            return True
        else:
            print(f"微信推送失败: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"微信推送出错: {e}")
        return False

def run_daily():
    """设置每日运行的任务"""
    print("设置每天早上8点自动生成大模型日报...")
    schedule.every().day.at("08:00").do(generate_daily_report)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

def run_now():
    """立即运行一次"""
    return generate_daily_report()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='大模型新闻自动日报生成器')
    parser.add_argument('--now', action='store_true', help='立即运行一次')
    parser.add_argument('--schedule', action='store_true', help='设置定时运行')
    parser.add_argument('--sendkey', type=str, help='设置Server酱SendKey用于微信推送')
    
    args = parser.parse_args()
    
    # 如果提供了SendKey参数，则更新全局变量
    if args.sendkey:
        SERVERCHAN_SEND_KEY = args.sendkey
        print(f"已设置Server酱SendKey，微信推送功能已启用")
    
    if args.now:
        run_now()
    elif args.schedule:
        run_daily()
    else:
        # 默认立即运行一次，并显示帮助信息
        run_now()
        print("\n使用说明:")
        print("  --now: 立即生成一次日报")
        print("  --schedule: 设置每天自动运行")
        print("  --sendkey KEY: 设置Server酱SendKey用于微信推送") 
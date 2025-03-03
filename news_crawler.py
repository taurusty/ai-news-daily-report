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
import argparse
from datetime import datetime

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

# 定义可用的主题
TOPICS = {
    "1": {
        "name": "大模型",
        "keywords": ["大模型", "GPT", "人工智能", "AI大模型", "AIGC", "LLM", "生成式AI"],
        "report_name": "大模型日报"
    },
    "2": {
        "name": "凝血抗凝",
        "keywords": ["凝血", "抗凝", "血栓", "抗凝药", "华法林", "肝素", "血小板", "凝血因子", "抗血栓"],
        "report_name": "凝血抗凝日报"
    }
}

# 默认主题
DEFAULT_TOPIC = "1"

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

def fetch_wechat_news(topic_id=DEFAULT_TOPIC):
    """从搜狗微信获取特定主题相关新闻"""
    topic = TOPICS.get(topic_id, TOPICS[DEFAULT_TOPIC])
    print(f"开始获取{topic['name']}相关新闻...")
    
    news_items = []
    keywords = topic["keywords"]
    
    # 对每个关键词进行搜索
    for keyword in keywords:
        print(f"搜索关键词: {keyword}")
        url = "https://weixin.sogou.com/weixin"
        params = {
            "type": 2,
            "query": keyword,
            "ie": "utf8",
            "s_from": "input",
            "from": "input",
            "_sug_": "n",
            "_sug_type_": "",
        }
        
        headers = get_random_headers()
        try:
            response = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.select("ul.news-list li")
                
                print(f"找到 {len(articles)} 篇与 '{keyword}' 相关的微信公众号文章")
                
                for article in articles:
                    try:
                        # 提取标题和链接
                        title_elem = article.select_one("h3 a")
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        article_url = title_elem.get("href")
                        if article_url.startswith('/'):
                            article_url = "https://weixin.sogou.com" + article_url
                        
                        # 提取公众号名称
                        source_elem = article.select_one(".account")
                        source = source_elem.get_text(strip=True) if source_elem else "未知公众号"
                        
                        # 提取发布时间
                        time_elem = article.select_one(".s2")
                        pub_time = time_elem.get_text(strip=True) if time_elem else ""
                        
                        # 提取摘要
                        summary_elem = article.select_one(".txt-info")
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""
                        
                        # 计算热度分数
                        heat_score = calculate_wechat_heat(source, title, pub_time, keyword)
                        
                        # 创建新闻条目
                        news_item = NewsItem(
                            title=title,
                            url=article_url,
                            source=source,
                            date=datetime.now().strftime("%Y-%m-%d"),
                            summary=summary,
                            heat_score=heat_score
                        )
                        
                        # 检查是否已存在相同标题或URL的新闻
                        if not any(item.title == title or item.url == article_url for item in news_items):
                            news_items.append(news_item)
                        
                    except Exception as e:
                        print(f"处理微信公众号文章时出错: {e}")
                        continue
            else:
                print(f"请求失败，状态码: {response.status_code}")
                
        except Exception as e:
            print(f"搜索关键词 '{keyword}' 时出错: {e}")
        
        # 每个关键词搜索后休眠，避免频繁请求
        time.sleep(random.uniform(3, 5))
    
    print(f"总共获取了 {len(news_items)} 条微信公众号文章")
    return news_items

def calculate_wechat_heat(account_name, title, pub_time, keyword):
    """计算微信公众号文章的热度分数"""
    # 基础分数
    base_score = 50
    
    # 公众号权重分数 (知名公众号加分)
    account_score = 0
    important_accounts = [
        "中国医学论坛报", "医脉通", "丁香医生", "医学界", "中华医学杂志", 
        "NEJM医学前沿", "柳叶刀", "血栓与止血", "中华血液学杂志", "中国循环杂志"
    ]
    
    if account_name in important_accounts:
        account_score = 20
    elif "医" in account_name or "健康" in account_name or "血液" in account_name or "心脏" in account_name:
        account_score = 10
    
    # 标题相关性分数
    title_score = 0
    if keyword in title:
        title_score = 15
    
    # 时间衰减因子 (越新的文章分数越高)
    time_score = 0
    if pub_time:
        try:
            # 尝试解析发布时间
            if "小时前" in pub_time:
                hours = int(pub_time.replace("小时前", "").strip())
                time_score = max(15 - hours * 0.5, 0)  # 每小时减少0.5分，最低0分
            elif "天前" in pub_time:
                days = int(pub_time.replace("天前", "").strip())
                time_score = max(10 - days * 2, 0)  # 每天减少2分，最低0分
            elif "刚刚" in pub_time:
                time_score = 15
            elif "月" in pub_time and "日" in pub_time:
                # 处理"3月1日"格式
                current_year = datetime.now().year
                month_day = pub_time.split(" ")[0]  # 取日期部分
                month = int(month_day.split("月")[0])
                day = int(month_day.split("月")[1].replace("日", ""))
                
                pub_date = datetime(current_year, month, day)
                days_diff = (datetime.now() - pub_date).days
                
                time_score = max(10 - days_diff * 2, 0)
        except Exception as e:
            print(f"解析发布时间出错: {e}")
    
    # 计算总分
    total_score = base_score + account_score + title_score + time_score
    
    return min(total_score, 100)  # 最高100分

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

def generate_daily_report(topic_id=DEFAULT_TOPIC):
    """生成每日新闻报告，根据指定的主题"""
    topic = TOPICS.get(topic_id, TOPICS[DEFAULT_TOPIC])
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"开始生成{topic['name']}日报 ({today})...")
    
    # 获取新闻数据
    news_items = fetch_wechat_news(topic_id)
    
    if not news_items:
        print(f"未找到{topic['name']}相关新闻，日报生成失败")
        return None
    
    # 按热度排序，取前10条
    news_items.sort(key=lambda x: x.heat_score, reverse=True)
    top_news = news_items[:10]
    
    # 确保所有文章都有摘要
    for item in top_news:
        if not item.summary or len(item.summary) < 50:
            print(f"获取文章摘要: {item.title}")
            item.summary = extract_wechat_article_summary(item.url)
    
    # 保存为CSV
    report_filename = f"{topic['report_name']}_{today}.csv"
    report_path = os.path.join(DATA_DIR, report_filename)
    with open(report_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['日期', '标题', '内容摘要', '信息来源', 'URL', '热度'])
        
        for item in top_news:
            # 清理字段，确保没有换行符和额外的逗号
            title = item.title.replace('\n', ' ').replace('\r', '')
            summary = item.summary.replace('\n', ' ').replace('\r', '') if item.summary else ""
            source = item.source.replace('\n', ' ').replace('\r', '')
            
            writer.writerow([
                today,
                title,
                summary,
                source,
                item.url,
                item.heat_score
            ])
    
    print(f"{topic['report_name']}已保存到: {report_path}")
    
    # 如果设置了Server酱SendKey，推送到微信
    if SERVERCHAN_SEND_KEY:
        print("推送到微信...")
        push_to_wechat(top_news, today, topic_id)
    else:
        print("未配置Server酱SendKey，跳过微信推送")
    
    return report_path

def push_to_wechat(news_items, date, topic_id=DEFAULT_TOPIC):
    """将日报推送到微信"""
    if not SERVERCHAN_SEND_KEY:
        print("未配置Server酱SendKey，无法推送到微信")
        return False
    
    topic = TOPICS.get(topic_id, TOPICS[DEFAULT_TOPIC])
    
    # 构建标题
    title = f"{topic['report_name']} ({date})"
    
    # 构建正文内容（Markdown格式）
    content = f"# {title}\n\n## 今日热点新闻：\n\n"
    
    # 添加每条新闻
    for i, item in enumerate(news_items, 1):
        summary = item.summary[:100] + "..." if item.summary and len(item.summary) > 100 else (item.summary or "无摘要")
        content += f"{i}. [{item.title}]({item.url}) | 来源: {item.source} | 热度: {item.heat_score}\n"
        content += f"   > {summary}\n\n"
    
    # 添加日报生成时间
    content += f"\n\n---\n*日报生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    
    # 发送到Server酱
    server_url = f"https://sctapi.ftqq.com/{SERVERCHAN_SEND_KEY}.send"
    payload = {
        "title": title,
        "desp": content
    }
    
    try:
        response = requests.post(server_url, data=payload)
        result = json.loads(response.text)
        
        if result.get("code") == 0:
            print("微信推送成功！")
            return True
        else:
            print(f"微信推送失败: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"微信推送出错: {e}")
        return False

def run_daily(topic_id=DEFAULT_TOPIC, send_key=None):
    """设置每天定时运行"""
    if send_key:
        global SERVERCHAN_SEND_KEY
        SERVERCHAN_SEND_KEY = send_key
        print(f"Server酱SendKey已设置")
    
    print(f"已设置每天早上8:00自动生成{TOPICS[topic_id]['name']}日报...")
    schedule.every().day.at("08:00").do(generate_daily_report, topic_id)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def run_now(topic_id=DEFAULT_TOPIC, send_key=None):
    """立即运行一次"""
    if send_key:
        global SERVERCHAN_SEND_KEY
        SERVERCHAN_SEND_KEY = send_key
        print(f"Server酱SendKey已设置")
    
    generate_daily_report(topic_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自动生成特定主题的日报并推送到微信")
    
    # 创建互斥组，确保--now和--schedule不能同时使用
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--now", action="store_true", help="立即运行一次")
    group.add_argument("--schedule", action="store_true", help="设置每天自动运行")
    
    # 添加主题选择参数
    parser.add_argument("--topic", choices=["1", "2"], default=DEFAULT_TOPIC, 
                      help="选择主题: 1=大模型, 2=凝血抗凝")
    
    # 添加Server酱SendKey参数
    parser.add_argument("--sendkey", type=str, help="Server酱SendKey，用于推送到微信")
    
    args = parser.parse_args()
    
    if args.now:
        run_now(args.topic, args.sendkey)
    elif args.schedule:
        run_daily(args.topic, args.sendkey)
    else:
        print("自动新闻日报生成工具")
        print("\n用法:")
        print("  立即生成一次: python news_crawler.py --now [--topic {1,2}] [--sendkey YOUR_SENDKEY]")
        print("  设置每天自动运行: python news_crawler.py --schedule [--topic {1,2}] [--sendkey YOUR_SENDKEY]")
        print("\n主题选项:")
        for key, value in TOPICS.items():
            print(f"  {key} = {value['name']}")
        print("\n示例:")
        print("  python news_crawler.py --now --topic 1 --sendkey YOUR_SENDKEY")
        
        # 默认行为：立即运行一次
        run_now(DEFAULT_TOPIC) 
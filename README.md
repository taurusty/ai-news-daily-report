# 大模型新闻自动日报生成器

该项目是一个自动化工具，用于每天自动爬取和汇总关于特定主题（如大模型、凝血抗凝医学）方面的新闻，并将其总结成日报形式保存到本地CSV文件中。同时，还可以将日报内容推送到您的微信上，方便随时查看最新动态。

## 功能特点

- 支持多个主题的新闻爬取（目前支持：大模型、凝血抗凝）
- 自动从微信公众号文章中爬取相关新闻
- 按热度排序，筛选出最热门的前10条新闻
- 自动提取新闻摘要
- 将结果以CSV格式保存在本地，包含日期、标题、内容摘要、信息来源（公众号名称）、URL等信息
- 支持定时运行，每天自动生成日报
- **微信推送功能**：支持将日报内容推送到微信，随时掌握最新动态

## 项目结构

```
.
├── README.md               # 项目说明文档
├── daily_reports/          # 存放生成的日报CSV文件的目录
├── news_crawler.py         # 主程序文件
└── requirements.txt        # 项目依赖清单
```

## 安装依赖

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/ai-news-daily-report.git
cd ai-news-daily-report

# 创建报告目录（如果不存在）
mkdir -p daily_reports

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 选择主题

目前支持两个主题：
- `1` - 大模型：爬取人工智能大模型相关新闻
- `2` - 凝血抗凝：爬取医学领域凝血抗凝相关新闻

### 立即运行一次

```bash
# 默认爬取大模型主题
python news_crawler.py --now

# 指定爬取凝血抗凝主题
python news_crawler.py --now --topic 2
```

### 设置为每天自动运行

```bash
# 默认爬取大模型主题
python news_crawler.py --schedule

# 指定爬取凝血抗凝主题
python news_crawler.py --schedule --topic 2
```

此模式将设置程序在每天早上8:00自动运行，生成当天的新闻日报。

### 启用微信推送功能

要启用微信推送功能，您需要先获取Server酱的SendKey：

1. 访问 [Server酱官网](https://sct.ftqq.com/) 并登录
2. 获取您的SendKey
3. 在运行脚本时使用`--sendkey`参数：

```bash
# 立即爬取大模型主题并推送到微信
python news_crawler.py --now --sendkey 您的SendKey

# 立即爬取凝血抗凝主题并推送到微信
python news_crawler.py --now --topic 2 --sendkey 您的SendKey

# 设置每天自动爬取大模型主题并推送到微信
python news_crawler.py --schedule --sendkey 您的SendKey

# 设置每天自动爬取凝血抗凝主题并推送到微信
python news_crawler.py --schedule --topic 2 --sendkey 您的SendKey
```

您也可以直接在脚本中设置SendKey：打开`news_crawler.py`文件，找到`SERVERCHAN_SEND_KEY = ""`这一行，将您的SendKey填入引号中即可。

### 默认模式

直接运行脚本（不带参数）将立即生成一次大模型日报，并显示帮助信息：

```bash
python news_crawler.py
```

## 输出文件

日报文件将保存在`daily_reports`目录下，文件名格式为：
- 大模型主题：`大模型日报_YYYY-MM-DD.csv`
- 凝血抗凝主题：`凝血抗凝日报_YYYY-MM-DD.csv`

## 微信推送效果

推送到微信的内容会以markdown格式呈现，包含以下内容：
- 标题（主题和日期）
- 热点新闻列表（按热度排序）
- 每条新闻的标题、来源（公众号名称）、热度、摘要及原文链接
- 日报生成时间

示例推送效果：

```
# 大模型日报 (2025-03-03)

## 今日热点新闻：

1. [国内首个主动健康AI大模型在广州发布](https://mp.weixin.qq.com/s/xxx) | 来源: 健康时报 | 热度: 90
   > 2月28日，广东省第二人民医院联合华为技术有限公司在广州发布两个健康AI大模型——叮呗健康大模型与数智超声大模型...

2. [GPT-4如何改变教育？专家观点解析](https://mp.weixin.qq.com/s/yyy) | 来源: AI教育前沿 | 热度: 85
   > 随着人工智能技术的飞速发展，GPT-4等大型语言模型正在深刻改变教育领域...

...
```

## 技术实现

- 通过`requests`和`BeautifulSoup`实现网页爬取和解析
- 使用搜狗微信搜索作为数据源，获取多个关键词相关的微信公众号文章
- 热度计算算法综合考虑公众号权重、文章时效性、标题关键词匹配度等因素
- 使用`jieba`库进行中文分词和关键词提取
- 采用`schedule`库实现定时任务执行
- 使用Server酱(ServerChan)实现微信推送功能

## 定制化与扩展

如果需要调整爬取的内容或其他功能，可以直接修改`news_crawler.py`文件中的相关函数：

- `fetch_wechat_news()`: 修改爬取逻辑或搜索关键词
- `calculate_wechat_heat()`: 调整热度计算算法
- `extract_wechat_article_summary()`: 改进微信文章摘要提取方法
- `generate_daily_report()`: 调整日报生成逻辑和格式
- `push_to_wechat()`: 修改微信推送的内容格式
- `TOPICS`: 添加新的主题及其关键词

## 常见问题

1. **Q: 如何在服务器上持续运行此脚本？**
   A: 可以使用`nohup`命令或设置系统的`crontab`任务：
   ```bash
   nohup python news_crawler.py --schedule --topic 1 &
   ```

2. **Q: 运行时提示"需要验证码"怎么办？**
   A: 搜狗微信搜索有反爬机制，可以尝试以下方法：
   - 降低爬取频率（修改代码中的`time.sleep`参数）
   - 使用代理IP
   - 更换网络环境
   - 临时使用浏览器手动完成验证码

3. **Q: CSV文件中的中文显示乱码怎么办？**
   A: 确保使用支持UTF-8编码的编辑器或Excel导入工具打开CSV文件。

4. **Q: 如何添加新的主题？**
   A: 在`news_crawler.py`文件中找到`TOPICS`字典，按照现有格式添加新主题及其关键词。

## 贡献指南

欢迎对本项目提出改进建议或直接贡献代码：

1. Fork本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个Pull Request

## 许可证

该项目采用MIT许可证。详见 [LICENSE](LICENSE) 文件。

## 免责声明

本项目仅供学习和研究使用，请勿用于商业用途。使用本工具获取的新闻内容版权归原作者和微信公众号所有。使用本工具时请遵守相关法律法规和网站的使用条款。 
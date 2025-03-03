# 大模型新闻自动日报生成器

该项目是一个自动化工具，用于每天自动爬取和汇总关于大模型（AI大语言模型）方面的新闻，并将其总结成日报形式保存到本地CSV文件中。同时，还可以将日报内容推送到您的微信上，方便随时查看最新动态。

## 功能特点

- 自动从多个来源（百度新闻、新浪新闻等）爬取大模型相关新闻
- 按热度排序，筛选出最热门的前10条新闻
- 自动提取新闻摘要
- 将结果以CSV格式保存在本地，包含日期、标题、内容摘要、信息来源、URL等信息
- 支持定时运行，每天自动生成日报
- **微信推送功能**：支持将日报内容推送到微信，随时掌握大模型领域最新动态

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

### 立即运行一次

```bash
python news_crawler.py --now
```

### 设置为每天自动运行

```bash
python news_crawler.py --schedule
```

此模式将设置程序在每天早上8:00自动运行，生成当天的大模型新闻日报。

### 启用微信推送功能

要启用微信推送功能，您需要先获取Server酱的SendKey：

1. 访问 [Server酱官网](https://sct.ftqq.com/) 并登录
2. 获取您的SendKey
3. 在运行脚本时使用`--sendkey`参数：

```bash
python news_crawler.py --now --sendkey 您的SendKey
```

或者设置为每天自动运行并推送到微信：

```bash
python news_crawler.py --schedule --sendkey 您的SendKey
```

您也可以直接在脚本中设置SendKey：打开`news_crawler.py`文件，找到`SERVERCHAN_SEND_KEY = ""`这一行，将您的SendKey填入引号中即可。

### 默认模式

直接运行脚本（不带参数）将立即生成一次日报，并显示帮助信息：

```bash
python news_crawler.py
```

## 输出文件

日报文件将保存在`daily_reports`目录下，文件名格式为`大模型日报_YYYY-MM-DD.csv`。

## 微信推送效果

推送到微信的内容会以markdown格式呈现，包含以下内容：
- 标题（日期）
- 热点新闻列表（按热度排序）
- 每条新闻的标题、来源、热度、摘要及原文链接
- 日报生成时间

示例推送效果：

```
# 大模型日报 (2025-03-03)

## 今日热点新闻：

1. [国内首个主动健康AI大模型在广州发布](https://baijiahao.baidu.com/s?id=1825531155030492468) | 来源: 广州日报 | 热度: 90
   > 2月28日，广东省第二人民医院联合华为技术有限公司在广州发布两个健康AI大模型——叮呗健康大模型与数智超声大模型...

2. [周鸿祎:AI大模型引领教育变革 个性化教学的未来已来](https://baijiahao.baidu.com/s?id=1825535603672215357) | 来源: 未来网 | 热度: 90
   > 近日，全国政协委员、360集团创始人周鸿祎在接受中国少年报·未来网记者采访时，就AI大模型如何更好地融入教育体系...

...
```

## 技术实现

- 通过`requests`和`BeautifulSoup`实现网页爬取和解析
- 使用`jieba`库进行中文分词和关键词提取
- 采用`schedule`库实现定时任务执行
- 热度计算算法综合考虑新闻的来源权重、时效性和关键词匹配度
- 使用Server酱(ServerChan)实现微信推送功能

## 定制化与扩展

如果需要调整爬取的新闻来源、热度计算方式或其他功能，可以直接修改`news_crawler.py`文件中的相关函数：

- `fetch_baidu_news()` 和 `fetch_sina_news()`: 修改爬取逻辑或添加新的新闻来源
- `extract_keywords()`: 自定义关键词提取方式
- `generate_daily_report()`: 调整日报生成逻辑和格式
- `push_to_wechat()`: 修改微信推送的内容格式

## 常见问题

1. **Q: 如何在服务器上持续运行此脚本？**
   A: 可以使用`nohup`命令或设置系统的`crontab`任务：
   ```bash
   nohup python news_crawler.py --schedule &
   ```

2. **Q: 如何添加更多新闻源？**
   A: 参考现有的`fetch_baidu_news()`和`fetch_sina_news()`函数，编写新的爬取函数，并在`generate_daily_report()`中调用。

3. **Q: CSV文件中的中文显示乱码怎么办？**
   A: 确保使用支持UTF-8编码的编辑器或Excel导入工具打开CSV文件。

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

本项目仅供学习和研究使用，请勿用于商业用途。使用本工具获取的新闻内容版权归原作者和新闻源所有。使用本工具时请遵守相关法律法规和网站的使用条款。 
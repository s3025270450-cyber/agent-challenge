# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai",
# ]
# ///

import os
import json
import sys
import time
from openai import OpenAI

# ==========================================
# 配置区域
# ==========================================
API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 改为阿里云
BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_NAME = os.getenv("DASHSCOPE_MODEL_NAME", "qwen-plus")

if not API_KEY:
    print("❌ Error: 请设置环境变量 DASHSCOPE_API_KEY")
    sys.exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

class LongArticleAgent:
    def __init__(self, topic):
        self.topic = topic
        self.outline = []
        self.articles = []

    def step1_generate_outline(self):
        """Step 1: 生成章节大纲"""
        print(f"📋 正在规划主题: {self.topic}...")
        
        # 改进的 Prompt
        prompt = f"""
        请为主题《{self.topic}》生成一个包含3个章节的大纲。
        每个章节的标题应简洁明了，能够概括该部分的核心内容。
        输出格式必须是严格的JSON数组，例如：
        ["第一章：引言", "第二章：技术原理", "第三章：未来展望"]
        不要包含任何其他解释或文本。
        """
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是一个专业的写作规划师，只输出JSON数组，不要输出任何其他内容。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            
            # 清理可能的 Markdown 代码块（如 ```json ... ```）
            content = content.strip()
            if content.startswith("```"):
                # 移除开头和结尾的 ```
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            
            # 解析 JSON
            data = json.loads(content)
            
            # 处理返回的数据：可能直接是列表，也可能是包含列表的字典
            if isinstance(data, list):
                self.outline = data
            elif isinstance(data, dict):
                # 尝试找到第一个列表值
                for value in data.values():
                    if isinstance(value, list):
                        self.outline = value
                        break
                else:
                    raise ValueError("返回的JSON中未找到列表")
            else:
                raise ValueError("返回的数据格式异常")
            
            if not self.outline:
                raise ValueError("大纲列表为空")

            print(f"✅ 大纲已生成: {self.outline}")

        except Exception as e:
            print(f"❌ 大纲生成失败: {e}")
            print(f"Raw Content: {content if 'content' in locals() else 'None'}")
            sys.exit(1)

    def step2_generate_content_loop(self):
        """Step 2: 循环生成内容，并维护 Context"""
        if not self.outline:
            return

        # 初始化上下文摘要
        previous_summary = "文章开始。"
    
        print("\n🚀 开始撰写正文...")
        for i, chapter in enumerate(self.outline):
            print(f"[{i+1}/{len(self.outline)}] 正在撰写: {chapter}...")
        
        # 构造 Prompt，核心在于 Context 的注入
            prompt = f"""
        你是一位专业作家。请撰写章节："{chapter}"。

        【前情提要】：
        {previous_summary}

        要求：
        1. 内容充实，字数约 300 字。
        2. 必须承接【前情提要】的逻辑，不要重复前文内容。
        3. 语言流畅，逻辑清晰。
        """
            
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=800  # 控制输出长度，避免过长
                )
                content = response.choices[0].message.content
                self.articles.append(f"## {chapter}\n\n{content}")
                
                # 更新 Context：截取最后 200 字作为下一章的前情提要
                # 更高级的方法：让模型对本章生成一个摘要，但简单截取也可以
                previous_summary = content[-200:]  # 取最后200字符，注意是中文字符
                
            except Exception as e:
                print(f"⚠️ 章节 {chapter} 生成失败: {e}")
                # 如果失败，可以选择跳过或使用备选摘要
                continue

    def save_result(self):
        if not self.articles:
            print("⚠️ 没有生成任何内容")
            return
            
        filename = "final_article.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {self.topic}\n\n")
            f.write("\n\n".join(self.articles))
        print(f"\n🎉 文章已保存至 {filename}")

if __name__ == "__main__":
    print(f"🔌 Endpoint: {BASE_URL}")
    print(f"🧠 Model: {MODEL_NAME}\n")
    
    agent = LongArticleAgent("2025年 DeepSeek 对 AI 行业的影响")
    agent.step1_generate_outline()
    agent.step2_generate_content_loop()
    agent.save_result()
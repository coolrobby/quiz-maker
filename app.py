import streamlit as st
import pandas as pd
import os
import json
import zipfile
from io import BytesIO
import shutil
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="题目大师 - 智能题库生成器",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    
    .stFileUploader {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    .upload-text {
        color: #667eea;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .success-box {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 1px solid #28a745;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #155724;
    }
    
    .error-box {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border: 1px solid #dc3545;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #721c24;
    }
    
    .info-box {
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
        border: 1px solid #17a2b8;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #0c5460;
    }
    
    .download-section {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin: 2rem 0;
    }
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        display: block;
    }
    
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    .header-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .subtitle {
        text-align: center;
        color: #6c757d;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

def load_template(template_name):
    """加载HTML模板"""
    template_path = os.path.join("templates", template_name)
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def detect_question_type(row):
    """智能识别题目类型"""
    options = [str(row.get('选项A', '')), str(row.get('选项B', '')), 
               str(row.get('选项C', '')), str(row.get('选项D', ''))]
    
    # 过滤空选项
    valid_options = [opt for opt in options if opt.strip() and opt.strip().lower() != 'nan']
    
    if len(valid_options) == 0:
        return 'fill'  # 填空题
    elif len(valid_options) >= 2:
        return 'choice'  # 选择题
    else:
        return 'fill'  # 只有一个选项，当作填空题处理

def process_excel_file(uploaded_file):
    """处理Excel文件并生成题目数据"""
    try:
        # 读取Excel文件
        df = pd.read_excel(uploaded_file)
        
        # 检查必需的列
        required_columns = ['题干', '答案']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return None, f"缺少必需的列: {', '.join(missing_columns)}"
        
        # 处理数据
        questions = []
        stats = {
            'total': len(df),
            'choice': 0,
            'fill': 0,
            'choice_3': 0,
            'choice_4': 0
        }
        
        for index, row in df.iterrows():
            # 检测题目类型
            question_type = detect_question_type(row)
            
            # 构建题目数据
            question_data = {
                'question': str(row['题干']).strip(),
                'answer': str(row['答案']).strip(),
                'type': question_type
            }
            
            if question_type == 'choice':
                options = []
                for opt_col in ['选项A', '选项B', '选项C', '选项D']:
                    if opt_col in row and pd.notna(row[opt_col]):
                        opt_text = str(row[opt_col]).strip()
                        if opt_text and opt_text.lower() != 'nan':
                            options.append(opt_text)
                
                question_data['options'] = options
                stats['choice'] += 1
                
                if len(options) == 3:
                    stats['choice_3'] += 1
                elif len(options) == 4:
                    stats['choice_4'] += 1
            else:
                stats['fill'] += 1
            
            questions.append(question_data)
        
        return questions, stats
        
    except Exception as e:
        return None, f"处理文件时出错: {str(e)}"

def generate_html_file(questions, filename, stats):
    """生成HTML文件"""
    try:
        # 加载模板
        header_template = load_template("header.html")
        footer_template = load_template("footer.html")
        
        # 获取文件名（不含扩展名）
        base_filename = os.path.splitext(filename)[0]
        
        # 替换模板中的标题
        header_content = header_template.replace("{{title}}", base_filename)
        
        # 生成题目数据的JavaScript
        questions_js = f"const questionsData = {json.dumps(questions, ensure_ascii=False, indent=2)};"
        
        # 生成主要内容
        main_content = f"""
    <main class="content">
        <div class="container">
            <div class="quiz-container">
                <div class="quiz-header">
                    <h1 class="quiz-title">{base_filename}</h1>
                    
                    <div class="quiz-controls">
                        <div class="control-group">
                            <label for="shuffleQuestions">题目乱序：</label>
                            <label class="switch">
                                <input type="checkbox" id="shuffleQuestions">
                                <span class="slider"></span>
                            </label>
                        </div>
                        
                        <div class="control-group">
                            <label for="shuffleOptions">选项乱序：</label>
                            <label class="switch">
                                <input type="checkbox" id="shuffleOptions">
                                <span class="slider"></span>
                            </label>
                        </div>
                        
                        <button class="start-btn" id="startQuiz">开始答题</button>
                    </div>
                    
                    <div class="stats-info">
                        <p>📊 题目统计：总计 {stats['total']} 题，选择题 {stats['choice']} 题，填空题 {stats['fill']} 题</p>
                        {f'<p>📝 选择题详情：三选项 {stats["choice_3"]} 题，四选项 {stats["choice_4"]} 题</p>' if stats['choice'] > 0 else ''}
                    </div>
                </div>
                
                <div id="questionsContainer">
                    <div class="info-message">
                        <h3>📚 答题说明</h3>
                        <ul>
                            <li>🔀 可选择是否打乱题目和选项顺序</li>
                            <li>✅ 每题答完后立即显示对错</li>
                            <li>📊 完成后查看详细统计和错题回顾</li>
                            <li>⏱️ 系统会记录你的答题时间</li>
                            <li>🔄 可随时点击"交卷"查看成绩</li>
                        </ul>
                        <p style="text-align: center; margin-top: 20px;">
                            <strong>点击"开始答题"按钮开始挑战！</strong>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </main>
    
    <script>
    {questions_js}
    </script>
"""
        
        # 组合完整的HTML
        full_html = header_content + main_content + footer_template
        
        return full_html
        
    except Exception as e:
        return None

def create_backup():
    """创建项目备份"""
    try:
        # 生成带时间戳的备份文件夹名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_base_dir = "D:\\BaiduSyncdisk\\坦克云课堂题目大师"
        backup_dir = os.path.join(backup_base_dir, f"坦克云课堂题目大师2_{timestamp}")
        current_dir = os.getcwd()
        
        # 确保备份目录存在
        os.makedirs(backup_dir, exist_ok=True)
        
        # 复制整个项目
        for item in os.listdir(current_dir):
            if item.startswith('.') or item == '__pycache__':
                continue
                
            source_path = os.path.join(current_dir, item)
            dest_path = os.path.join(backup_dir, item)
            
            if os.path.isdir(source_path):
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)
        
        return True, "备份成功"
    except Exception as e:
        return False, str(e)

def main():
    """主函数"""
    # 页面标题
    st.markdown('<h1 class="header-title">📚 题目大师</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">智能题库生成器 - 让学习更高效</p>', unsafe_allow_html=True)
    
    # 功能介绍
    with st.expander("📖 功能介绍", expanded=False):
        st.markdown("""
        ### 🎯 核心功能
        - **📁 批量上传**：支持同时上传多个Excel文件
        - **🤖 智能识别**：自动识别选择题（2-4选项）和填空题
        - **📱 移动优化**：完美适配手机、平板、电脑
        - **🔀 灵活控制**：用户可控制题目和选项乱序
        - **📊 详细统计**：完整的答题报告和错题回顾
        
        ### 📋 Excel格式要求
        | 列名 | 说明 | 必需 |
        |------|------|------|
        | 题干 | 题目内容 | ✅ |
        | 选项A | 第一个选项 | ❌ |
        | 选项B | 第二个选项 | ❌ |
        | 选项C | 第三个选项 | ❌ |
        | 选项D | 第四个选项 | ❌ |
        | 答案 | 正确答案 | ✅ |
        
        ### 💡 智能识别规则
        - **四选项选择题**：ABCD四个选项都有内容
        - **三选项选择题**：ABC有内容，D选项为空
        - **填空题**：所有选项字段为空
        """)
    
    # 文件上传区域
    st.markdown('<div class="upload-text">📁 上传Excel文件</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "选择Excel文件",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        help="支持批量上传多个Excel文件"
    )
    
    if uploaded_files:
        st.markdown('<div class="success-box">✅ 文件上传成功！正在处理...</div>', unsafe_allow_html=True)
        
        # 处理文件
        processed_files = []
        total_stats = {'total': 0, 'choice': 0, 'fill': 0, 'choice_3': 0, 'choice_4': 0}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"正在处理: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
            
            # 处理Excel文件
            questions, stats = process_excel_file(uploaded_file)
            
            if questions is None:
                st.error(f"❌ 处理文件 {uploaded_file.name} 时出错: {stats}")
                continue
            
            # 生成HTML文件
            html_content = generate_html_file(questions, uploaded_file.name, stats)
            
            if html_content is None:
                st.error(f"❌ 生成HTML文件 {uploaded_file.name} 时出错")
                continue
            
            # 保存处理结果
            processed_files.append({
                'filename': uploaded_file.name,
                'html_filename': os.path.splitext(uploaded_file.name)[0] + '.html',
                'html_content': html_content,
                'stats': stats
            })
            
            # 更新总统计
            for key in total_stats:
                total_stats[key] += stats[key]
            
            # 更新进度
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.text("处理完成！")
        
        if processed_files:
            # 显示统计信息
            st.markdown('<div class="success-box">🎉 所有文件处理完成！</div>', unsafe_allow_html=True)
            
            # 统计卡片
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <span class="stat-number">{len(processed_files)}</span>
                    <div class="stat-label">生成文件</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <span class="stat-number">{total_stats['total']}</span>
                    <div class="stat-label">总题数</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="stat-card">
                    <span class="stat-number">{total_stats['choice']}</span>
                    <div class="stat-label">选择题</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="stat-card">
                    <span class="stat-number">{total_stats['fill']}</span>
                    <div class="stat-label">填空题</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 文件详情
            with st.expander("📊 文件处理详情", expanded=True):
                for file_info in processed_files:
                    st.markdown(f"""
                    **📄 {file_info['filename']}**
                    - 生成文件：{file_info['html_filename']}
                    - 总题数：{file_info['stats']['total']}
                    - 选择题：{file_info['stats']['choice']} 题
                    - 填空题：{file_info['stats']['fill']} 题
                    {f"- 三选项：{file_info['stats']['choice_3']} 题，四选项：{file_info['stats']['choice_4']} 题" if file_info['stats']['choice'] > 0 else ""}
                    """)
            
            # 下载区域
            st.markdown('<div class="download-section">', unsafe_allow_html=True)
            st.markdown("### 📥 下载生成的HTML文件")
            
            if len(processed_files) == 1:
                # 单个文件直接下载
                file_info = processed_files[0]
                st.download_button(
                    label=f"📄 下载 {file_info['html_filename']}",
                    data=file_info['html_content'].encode('utf-8'),
                    file_name=file_info['html_filename'],
                    mime="text/html",
                    use_container_width=True
                )
            else:
                # 多个文件打包下载
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_info in processed_files:
                        zip_file.writestr(
                            file_info['html_filename'],
                            file_info['html_content'].encode('utf-8')
                        )
                
                zip_buffer.seek(0)
                
                st.download_button(
                    label=f"📦 下载所有文件 ({len(processed_files)} 个HTML文件)",
                    data=zip_buffer.getvalue(),
                    file_name=f"题目大师_生成文件_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                
                # 单独下载选项
                st.markdown("**或单独下载：**")
                cols = st.columns(min(3, len(processed_files)))
                for i, file_info in enumerate(processed_files):
                    with cols[i % len(cols)]:
                        st.download_button(
                            label=f"📄 {file_info['html_filename']}",
                            data=file_info['html_content'].encode('utf-8'),
                            file_name=file_info['html_filename'],
                            mime="text/html",
                            key=f"download_{i}"
                        )
            
            st.markdown('</div>', unsafe_allow_html=True)
            

    
    # 使用说明
    with st.expander("📚 使用说明", expanded=False):
        st.markdown("""
        ### 🚀 快速开始
        1. **准备Excel文件**：按照格式要求准备题目文件
        2. **上传文件**：支持批量上传多个Excel文件
        3. **自动处理**：系统自动识别题目类型并生成HTML
        4. **下载使用**：下载生成的HTML文件，可离线使用
        
        ### 📱 HTML文件特性
        - **📱 移动优化**：完美适配手机端使用
        - **🔄 离线可用**：无需网络连接即可使用
        - **🎨 精美界面**：欧美大学风格设计
        - **📊 智能统计**：详细的答题报告和分析
        - **🔀 灵活控制**：用户可控制题目和选项乱序
        
        ### 💡 最佳实践
        - 建议每个Excel文件包含同一主题的题目
        - 选择题答案请填写具体选项内容，不要填写A、B、C、D
        - 填空题答案支持大小写不敏感匹配
        - 生成的HTML文件可直接分享给学生使用
        """)
    
    # 备份功能
    if st.button("💾 备份项目到百度网盘同步文件夹", use_container_width=True):
        with st.spinner("正在备份项目..."):
            success, result = create_backup()
            if success:
                st.success(f"✅ {result}")
            else:
                st.error(f"❌ 备份失败: {result}")
    
    # 页脚信息
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6c757d; padding: 2rem 0;">
        <p>📚 <strong>题目大师</strong> - 让学习更高效 | 🔧 基于 Streamlit 构建</p>
        <p>💡 支持选择题、填空题 | 📱 完美适配移动端 | 🎯 智能题型识别</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
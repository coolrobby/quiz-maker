import streamlit as st
import pandas as pd
import os
import json
import zipfile
from io import BytesIO
import shutil
from datetime import datetime
import ftplib
import random
import string

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
        margin: 0 0 2rem 0;
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

def process_excel_file(file_obj):
    """处理Excel文件并生成题目数据"""
    try:
        # 读取Excel文件
        if hasattr(file_obj, 'path'):  # 本地文件
            df = pd.read_excel(file_obj.path)
        else:  # 上传的文件
            df = pd.read_excel(file_obj)
        
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
                option_mapping = {}
                for i, opt_col in enumerate(['选项A', '选项B', '选项C', '选项D']):
                    if opt_col in row and pd.notna(row[opt_col]):
                        opt_text = str(row[opt_col]).strip()
                        if opt_text and opt_text.lower() != 'nan':
                            options.append(opt_text)
                            # 建立字母到选项内容的映射
                            option_mapping[chr(65 + i)] = opt_text  # A=65, B=66, C=67, D=68
                
                question_data['options'] = options
                
                # 将答案字母转换为对应的选项内容
                answer_letter = str(row['答案']).strip().upper()
                if answer_letter in option_mapping:
                    question_data['answer'] = option_mapping[answer_letter]
                
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

def test_ftp_connection():
    """测试FTP连接是否正常"""
    ftp = None
    try:
        # 从secrets获取FTP配置
        ftp_host = st.secrets["ftp"]
        ftp_user = st.secrets["user"]
        ftp_password = st.secrets["password"]
        
        # 验证配置是否为空
        if not ftp_host or ftp_host == "your-ftp-host.com":
            return False, "请在.streamlit/secrets.toml中配置正确的FTP主机地址"
        if not ftp_user or ftp_user == "your-ftp-username":
            return False, "请在.streamlit/secrets.toml中配置正确的FTP用户名"
        if not ftp_password or ftp_password == "your-ftp-password":
            return False, "请在.streamlit/secrets.toml中配置正确的FTP密码"
        
        # 连接FTP服务器
        ftp = ftplib.FTP()
        ftp.set_debuglevel(0)
        
        # 尝试连接
        if ':' in ftp_host:
            host, port = ftp_host.split(':')
            port = int(port)
        else:
            host = ftp_host
            port = 21
        
        ftp.connect(host, port, timeout=30)
        ftp.login(ftp_user, ftp_password)
        
        # 测试基本操作（列出根目录）
        ftp.nlst()
        
        ftp.quit()
        return True, "FTP连接测试成功！"
        
    except Exception as e:
        return False, f"FTP连接测试失败：{str(e)}"
    finally:
        if ftp:
            try:
                ftp.quit()
            except:
                try:
                    ftp.close()
                except:
                    pass

def upload_to_ftp(html_content, original_filename):
    """上传HTML文件到FTP服务器并返回访问链接"""
    ftp = None
    try:
        # 从secrets获取FTP配置
        ftp_host = st.secrets["ftp"]
        ftp_user = st.secrets["user"]
        ftp_password = st.secrets["password"]
        
        # 验证配置是否为空
        if not ftp_host or ftp_host == "your-ftp-host.com":
            return False, "请在.streamlit/secrets.toml中配置正确的FTP主机地址", None
        if not ftp_user or ftp_user == "your-ftp-username":
            return False, "请在.streamlit/secrets.toml中配置正确的FTP用户名", None
        if not ftp_password or ftp_password == "your-ftp-password":
            return False, "请在.streamlit/secrets.toml中配置正确的FTP密码", None
        
        # 生成新的文件名：tkykt.com + 当前日期时间 + 6位随机数
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = ''.join(random.choices(string.digits, k=6))
        new_filename = f"tkykt.com_{current_time}_{random_suffix}.html"
        
        # 连接FTP服务器
        ftp = ftplib.FTP()
        
        # 设置超时时间
        ftp.set_debuglevel(0)  # 关闭调试模式
        
        # 尝试连接（添加端口号和超时设置）
        try:
            # 如果主机名包含端口，分离主机和端口
            if ':' in ftp_host:
                host, port = ftp_host.split(':')
                port = int(port)
            else:
                host = ftp_host
                port = 21
            
            ftp.connect(host, port, timeout=30)
        except Exception as conn_error:
            return False, f"无法连接到FTP服务器 {ftp_host}：{str(conn_error)}。请检查主机地址是否正确，网络是否正常。", None
        
        # 登录
        try:
            ftp.login(ftp_user, ftp_password)
        except Exception as login_error:
            return False, f"FTP登录失败：{str(login_error)}。请检查用户名和密码是否正确。", None
        
        # 上传文件到根目录
        try:
            html_bytes = html_content.encode('utf-8')
            ftp.storbinary(f'STOR {new_filename}', BytesIO(html_bytes))
        except Exception as upload_error:
            return False, f"文件上传失败：{str(upload_error)}", None
        
        # 关闭FTP连接
        ftp.quit()
        
        # 生成访问链接（直接指向根目录）
        access_url = f"https://www.tkyktbackup.com/{new_filename}"
        
        return True, access_url, new_filename
        
    except KeyError as key_error:
        return False, f"配置错误：缺少必要的FTP配置项 {str(key_error)}。请检查.streamlit/secrets.toml文件。", None
    except Exception as e:
        return False, f"上传过程中发生未知错误：{str(e)}", None
    finally:
        # 确保FTP连接被关闭
        if ftp:
            try:
                ftp.quit()
            except:
                try:
                    ftp.close()
                except:
                    pass

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
        - **🔗 在线分享**：一键上传生成在线访问链接
        
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
    
    # FTP配置状态检查
    with st.expander("🔧 FTP配置状态", expanded=False):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            try:
                ftp_host = st.secrets.get("ftp", "未配置")
                ftp_user = st.secrets.get("user", "未配置")
                
                # 检查配置状态
                if (ftp_host == "未配置" or ftp_host == "your-ftp-host.com" or 
                    ftp_user == "未配置" or ftp_user == "your-ftp-username"):
                    st.warning("⚠️ FTP配置未完成，无法使用生成链接功能")
                    st.info("请编辑 `.streamlit/secrets.toml` 文件配置FTP服务器信息")
                else:
                    st.success(f"✅ FTP配置已完成 - 服务器: {ftp_host}, 用户: {ftp_user}")
                    
            except Exception:
                st.error("❌ 无法读取FTP配置，请检查 `.streamlit/secrets.toml` 文件")
        
        with col2:
            if st.button("🧪 测试连接", help="测试FTP服务器连接是否正常"):
                with st.spinner("正在测试FTP连接..."):
                    success, message = test_ftp_connection()
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    # 创建两个选项卡：从input文件夹选择和上传文件
    tab1, tab2 = st.tabs(["📂 从input文件夹选择", "📁 上传Excel文件"])
    
    uploaded_files = None
    selected_files = None
    
    with tab1:
        st.markdown('<div class="upload-text">📂 从input文件夹选择Excel文件</div>', unsafe_allow_html=True)
        
        # 获取input文件夹中的Excel文件
        input_folder = "input"
        if not os.path.exists(input_folder):
            os.makedirs(input_folder)
        
        excel_files = []
        if os.path.exists(input_folder):
            for file in os.listdir(input_folder):
                if file.lower().endswith(('.xlsx', '.xls')):
                    excel_files.append(file)
        
        if excel_files:
            st.markdown(f'<div class="info-box">📋 发现 {len(excel_files)} 个Excel文件</div>', unsafe_allow_html=True)
            
            # 多选框选择文件
            selected_file_names = st.multiselect(
                "选择要处理的Excel文件（可多选）",
                excel_files,
                help="可以选择多个文件进行批量处理"
            )
            
            if selected_file_names:
                # 创建文件对象列表
                selected_files = []
                for filename in selected_file_names:
                    file_path = os.path.join(input_folder, filename)
                    # 创建一个类似于uploaded_file的对象
                    class LocalFile:
                        def __init__(self, path, name):
                            self.path = path
                            self.name = name
                        
                        def read(self):
                            with open(self.path, 'rb') as f:
                                return f.read()
                    
                    selected_files.append(LocalFile(file_path, filename))
                
                st.markdown(f'<div class="success-box">✅ 已选择 {len(selected_files)} 个文件</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-box">📝 input文件夹中暂无Excel文件<br>请将Excel文件放入input文件夹，或使用上传功能</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="upload-text">📁 上传Excel文件</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "选择Excel文件",
            type=['xlsx', 'xls'],
            accept_multiple_files=True,
            help="支持批量上传多个Excel文件"
        )
    
    # 合并处理逻辑
    files_to_process = uploaded_files if uploaded_files else selected_files
    
    if files_to_process:
        if uploaded_files:
            st.markdown('<div class="success-box">✅ 文件上传成功！正在处理...</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="success-box">✅ 文件选择成功！正在处理...</div>', unsafe_allow_html=True)
        
        # 处理文件
        processed_files = []
        total_stats = {'total': 0, 'choice': 0, 'fill': 0, 'choice_3': 0, 'choice_4': 0}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, file_obj in enumerate(files_to_process):
            status_text.text(f"正在处理: {file_obj.name} ({i+1}/{len(files_to_process)})")
            
            # 处理Excel文件
            questions, stats = process_excel_file(file_obj)
            
            if questions is None:
                st.error(f"❌ 处理文件 {file_obj.name} 时出错: {stats}")
                continue
            
            # 生成HTML文件
            html_content = generate_html_file(questions, file_obj.name, stats)
            
            if html_content is None:
                st.error(f"❌ 生成HTML文件 {file_obj.name} 时出错")
                continue
            
            # 保存处理结果
            processed_files.append({
                'filename': file_obj.name,
                'html_filename': os.path.splitext(file_obj.name)[0] + '.html',
                'html_content': html_content,
                'stats': stats
            })
            
            # 更新总统计
            for key in total_stats:
                total_stats[key] += stats[key]
            
            # 更新进度
            progress_bar.progress((i + 1) / len(files_to_process))
        
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
            
            # HTML文件列表和预览区域
            st.markdown("### 📄 生成的HTML文件列表")
            
            # 显示所有生成的HTML文件
            for i, file_info in enumerate(processed_files):
                with st.expander(f"📄 {file_info['html_filename']} - {file_info['stats']['total']} 题", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"""
                        **文件信息：**
                        - 📁 原文件：{file_info['filename']}
                        - 📄 HTML文件：{file_info['html_filename']}
                        - 📊 总题数：{file_info['stats']['total']} 题
                        - ✅ 选择题：{file_info['stats']['choice']} 题
                        - ✏️ 填空题：{file_info['stats']['fill']} 题
                        {f"- 🔢 三选项：{file_info['stats']['choice_3']} 题，四选项：{file_info['stats']['choice_4']} 题" if file_info['stats']['choice'] > 0 else ""}
                        """)
                    
                    with col2:
                        # 创建两个子列用于下载和生成链接按钮
                        btn_col1, btn_col2 = st.columns(2)
                        
                        with btn_col1:
                            # 单个文件下载按钮
                            st.download_button(
                                label="📥 下载",
                                data=file_info['html_content'].encode('utf-8'),
                                file_name=file_info['html_filename'],
                                mime="text/html",
                                key=f"download_single_{i}",
                                use_container_width=True
                            )
                        
                        with btn_col2:
                            # 生成链接按钮
                            if st.button(
                                label="🔗 生成链接",
                                key=f"generate_link_{i}",
                                use_container_width=True,
                                help="上传到服务器并生成在线访问链接"
                            ):
                                # 显示上传进度
                                with st.spinner('正在上传到服务器...'):
                                    success, result, new_filename = upload_to_ftp(
                                        file_info['html_content'], 
                                        file_info['html_filename']
                                    )
                                
                                if success:
                                    st.success(f"✅ 上传成功！")
                                    st.info(f"📁 服务器文件名：{new_filename}")
                                    st.markdown(f"🔗 **访问链接：** [{result}]({result})")
                                    
                                    # 提供链接复制功能
                                    st.code(result, language=None)
                                    st.caption("💡 点击上方链接框可以选中并复制链接")
                                else:
                                    st.error(f"❌ 上传失败：{result}")
                                    st.info("请检查网络连接或联系管理员")
                    
                    # HTML预览区域
                    st.markdown("**📱 HTML预览：**")
                    
                    # 创建预览选项卡
                    preview_tab1, preview_tab2 = st.tabs(["🖥️ 渲染预览", "📝 源码预览"])
                    
                    with preview_tab1:
                         # 实际HTML预览 - 可以真正做题
                         st.markdown("**🎮 互动答题预览：**")
                         st.info("💡 下方是完整的答题界面，您可以直接体验做题功能！")
                         
                         # 使用streamlit的components.html来嵌入完整的HTML
                         import streamlit.components.v1 as components
                         
                         # 渲染完整的HTML内容，允许用户真正做题
                         components.html(
                             file_info['html_content'],
                             height=800,
                             scrolling=True
                         )
                         
                         # 添加使用提示
                         st.markdown("""
                         <div style="background: #e3f2fd; border: 1px solid #2196f3; border-radius: 8px; padding: 15px; margin: 10px 0;">
                             <h4 style="color: #1976d2; margin-top: 0;">🎯 预览说明</h4>
                             <ul style="color: #1565c0; margin-bottom: 0;">
                                 <li>✅ 上方是完整的答题界面，功能与下载的HTML文件完全一致</li>
                                 <li>🎮 您可以直接点击"开始答题"按钮体验完整的答题流程</li>
                                 <li>📊 支持题目乱序、选项乱序、答题统计等所有功能</li>
                                 <li>💾 如果满意效果，请使用右侧的下载按钮获取HTML文件</li>
                                 <li>📱 下载的HTML文件可以离线使用，完美适配手机端</li>
                             </ul>
                         </div>
                         """, unsafe_allow_html=True)
                    
                    with preview_tab2:
                        # 源码预览
                        st.markdown("**📝 HTML源码预览（前1000字符）：**")
                        preview_content = file_info['html_content'][:1000]
                        if len(file_info['html_content']) > 1000:
                            preview_content += "\n\n... (内容已截断，下载完整文件查看全部内容) ..."
                        
                        st.code(preview_content, language='html')
                        
                        st.info(f"📏 完整文件大小：{len(file_info['html_content'])} 字符")
            
            # 批量下载区域
            st.markdown("---")
            st.markdown("### 📦 批量下载")
            
            if len(processed_files) > 1:
                # 多个文件打包下载
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_info in processed_files:
                        zip_file.writestr(
                            file_info['html_filename'],
                            file_info['html_content'].encode('utf-8')
                        )
                
                zip_buffer.seek(0)
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"""
                    **📦 打包下载所有文件**
                    - 📁 包含文件：{len(processed_files)} 个HTML文件
                    - 📊 总题数：{total_stats['total']} 题
                    - 💾 压缩格式：ZIP
                    """)
                
                with col2:
                    st.download_button(
                        label=f"📦 下载全部 ({len(processed_files)} 个文件)",
                        data=zip_buffer.getvalue(),
                        file_name=f"题目大师_生成文件_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
            else:
                st.info("💡 只有一个文件时，请使用上方的单个下载按钮")
            
            st.markdown('</div>', unsafe_allow_html=True)
            

    

    
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
        <p>📚 <strong>题目大师</strong> - 让学习更高效 | 🔧 技术支持：川哥</p>
        <p>💡 支持选择题、填空题 | 📱 完美适配移动端 | 🎯 智能题型识别</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

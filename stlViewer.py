import streamlit as st
import pyvista as pv
from stpyvista import stpyvista
import numpy as np
from io import BytesIO
import tempfile
import os
import uuid
import json
import base64
from datetime import datetime
import requests  # 新增
from urllib.parse import urljoin  # 新增

# 辅助函数定义
def update_visibility(file_id):
    """更新单个文件的可见性"""
    current_value = st.session_state[f"vis_{file_id}"]
    st.session_state.uploaded_files[file_id]['visible'] = current_value


def set_all_visibility(visible):
    """设置所有文件的可见性"""
    for file_id in st.session_state.uploaded_files:
        st.session_state.uploaded_files[file_id]['visible'] = visible
    st.rerun()


def clear_all_files():
    """清空所有文件"""
    st.session_state.uploaded_files = {}
    st.session_state.file_processed = False
    st.rerun()


def save_session_state():
    """保存当前会话状态到文件"""
    session_data = {
        'uploaded_files': {},
        'timestamp': datetime.now().isoformat()
    }

    # 转换文件数据为base64编码
    for file_id, file_info in st.session_state.uploaded_files.items():
        session_data['uploaded_files'][file_id] = {
            'name': file_info['name'],
            'data': base64.b64encode(file_info['data']).decode('utf-8'),
            'size': file_info['size'],
            'visible': file_info['visible']
        }

    return json.dumps(session_data)


def load_session_state(session_json):
    """从JSON加载会话状态"""
    try:
        session_data = json.loads(session_json)
        st.session_state.uploaded_files = {}

        for file_id, file_info in session_data['uploaded_files'].items():
            st.session_state.uploaded_files[file_id] = {
                'name': file_info['name'],
                'data': base64.b64decode(file_info['data']),
                'size': file_info['size'],
                'visible': file_info['visible']
            }

        st.session_state.file_processed = True
        st.success("会话加载成功！")
        st.rerun()

    except Exception as e:
        st.error(f"加载会话失败: {str(e)}")


def fit_to_view():
    """调整视图使所有可见模型都在视野内"""
    if st.session_state.uploaded_files:
        # 创建一个临时绘图器来计算合适的相机位置
        temp_plotter = pv.Plotter(off_screen=True)

        # 添加所有可见的模型
        for file_id, file_info in st.session_state.uploaded_files.items():
            if file_info['visible']:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.stl') as tmp_file:
                    tmp_file.write(file_info['data'])
                    tmp_path = tmp_file.name

                try:
                    mesh = pv.read(tmp_path)
                    temp_plotter.add_mesh(mesh)
                except Exception as e:
                    st.error(f"处理模型 {file_info['name']} 时出错: {str(e)}")
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

        # 调整视图到适合所有模型
        temp_plotter.reset_camera()
        camera_position = temp_plotter.camera_position

        # 存储相机位置到session state
        st.session_state.camera_position = camera_position
        st.rerun()


def load_initial_model():
    """初始加载GitHub上的STL模型"""
    try:
        # 可以配置多个初始模型
        initial_models = [
            {
                "name": "Proj_491317_SP_model.stl",
                "url": "https://raw.githubusercontent.com/schaugo-tech/Proj_491317_1/main/models/Proj_491317_SP_model.stl"
            },
            {
                "name": "general_teeth_U.stl",
                "url": "https://raw.githubusercontent.com/schaugo-tech/Proj_491317_1/main/models/general_teeth_U.stl"
            }
        ]

        for model in initial_models:
            response = requests.get(model["url"], timeout=10)
            response.raise_for_status()

            file_id = str(uuid.uuid4())
            st.session_state.uploaded_files[file_id] = {
                'name': model["name"],
                'data': response.content,
                'size': len(response.content),
                'visible': True
            }

        st.session_state.file_processed = True
        return True

    except Exception as e:
        st.warning(f"初始模型加载失败: {str(e)}")
        return False


# 页面配置
st.set_page_config(
    page_title="多文件 STL 查看器",
    page_icon="🧊",
    layout="wide",
)

# 初始化 session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}
if 'file_processed' not in st.session_state:
    st.session_state.file_processed = False
if 'reset_view' not in st.session_state:
    st.session_state.reset_view = False
if 'initial_load_done' not in st.session_state:  # 新增
    st.session_state.initial_load_done = False

# 初始加载GitHub模型（只在第一次运行时执行）
if not st.session_state.initial_load_done and not st.session_state.uploaded_files:
    with st.spinner("正在加载初始模型..."):
        if load_initial_model():
            st.session_state.initial_load_done = True
            st.rerun()

# 应用标题
st.title("🧊 洲歌科技——模型可视化协作工具")
st.markdown("上传多个STL文件，选择显示或隐藏特定文件，支持保存和分享会话")

# 创建三列布局
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    # 文件上传器
    uploaded_files = st.file_uploader(
        "选择STL文件",
        type=['stl'],
        accept_multiple_files=True,
        key="file_uploader"
    )

    # 处理新上传的文件
    if uploaded_files and not st.session_state.file_processed:
        for uploaded_file in uploaded_files:
            file_exists = False
            for existing_file in st.session_state.uploaded_files.values():
                if existing_file['name'] == uploaded_file.name and existing_file['size'] == len(
                        uploaded_file.getvalue()):
                    file_exists = True
                    break

            if not file_exists:
                file_id = str(uuid.uuid4())
                st.session_state.uploaded_files[file_id] = {
                    'name': uploaded_file.name,
                    'data': uploaded_file.getvalue(),
                    'size': len(uploaded_file.getvalue()),
                    'visible': True
                }

        st.session_state.file_processed = True
        st.rerun()

    if not uploaded_files:
        st.session_state.file_processed = False

    # 文件管理选项
    st.subheader("文件管理")

    if st.session_state.uploaded_files:
        for file_id, file_info in st.session_state.uploaded_files.items():
            col_vis, col_name = st.columns([1, 4])
            with col_vis:
                visibility = st.checkbox(
                    "",
                    value=file_info['visible'],
                    key=f"vis_{file_id}",
                    on_change=lambda f_id=file_id: update_visibility(f_id)
                )

            with col_name:
                st.text(file_info['name'][:30] + ("..." if len(file_info['name']) > 30 else ""))

        col_act1, col_act2, col_act3 = st.columns(3)  # 改为3列
        with col_act1:
            if st.button("全部显示", use_container_width=True, key="show_all"):
                set_all_visibility(True)
        with col_act2:
            if st.button("全部隐藏", use_container_width=True, key="hide_all"):
                set_all_visibility(False)
        with col_act3:
            if st.button("📷 适应视图", use_container_width=True, key="fit_view"):
                fit_to_view()  # 调用新的适应视图函数

        if st.button("清空所有文件", type="secondary", use_container_width=True, key="clear_all"):
            clear_all_files()
    else:
        st.info("请上传一个或多个STL文件")

with col2:
    # 3D 渲染区域
    if st.session_state.uploaded_files:
        with st.spinner("加载和渲染模型中..."):
            plotter = pv.Plotter(window_size=[800, 600])
            # 如果有保存的相机位置，就应用它
            if 'camera_position' in st.session_state and st.session_state.camera_position:
                plotter.camera_position = st.session_state.camera_position
            colors = [
                '#D8E2DC',  # 灰粉色
                '#FFE5D9',  # 浅珊瑚色
                '#FEC89A',  # 浅杏色
                '#F9DCC4',  # 淡米色
                '#E8E8E4',  # 浅灰色
                '#D6E2E9',  # 灰蓝色
                '#EFD3D7',  # 淡紫粉色
                '#F2E8CF',  # 淡卡其色
                '#DDE5B6',  # 淡橄榄绿
                '#E0C3A0'  # 浅驼色
            ]
            color_idx = 0
            visible_count = 0
            legend_labels = []

            for file_id, file_info in st.session_state.uploaded_files.items():
                if file_info['visible']:
                    visible_count += 1

                    with tempfile.NamedTemporaryFile(delete=False, suffix='.stl') as tmp_file:
                        tmp_file.write(file_info['data'])
                        tmp_path = tmp_file.name

                    try:
                        mesh = pv.read(tmp_path)
                        color = colors[color_idx % len(colors)]
                        color_idx += 1

                        short_name = file_info['name']
                        if len(short_name) > 20:
                            short_name = short_name[:17] + "..."

                        ## plotter.add_mesh(
                        ##     mesh,
                        ##     color=color,
                        ##     show_edges=True,
                        ##     smooth_shading=True,
                        ##     label=short_name
                        ## )
                        plotter.add_mesh(
                            mesh,
                            color=color,
                            style='surface',  # 表面渲染
                            lighting=True,  # 启用光照
                            show_edges=False,  # 显示边缘
                            edge_color='black',  # 边缘颜色
                            line_width=1.5,  # 边缘线宽
                            smooth_shading=True,  # 平滑着色
                            specular=0.3,  # 高光强度
                            diffuse=0.7,  # 漫反射
                            ambient=0.2,  # 环境光
                            metallic=0.1,  # 金属质感
                            roughness=0.8,  # 粗糙度
                            interpolate_before_map=True,  # 预插值提高质量
                            label = short_name
                        )

                        legend_labels.append(short_name)

                    except Exception as e:
                        st.error(f"渲染模型 {file_info['name']} 时出错: {str(e)}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)

            if visible_count > 0:
                # 自动调整视图到所有可见模型
                plotter.reset_camera()
                plotter.add_axes()
                if legend_labels:
                    plotter.add_legend()

                stpyvista(plotter, key="pv_plotter")

                # 统计信息
                st.subheader("场景统计（建设中）")
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("可见文件数", visible_count)
                with col_stat2:
                    total_points = 0
                    for file_id, file_info in st.session_state.uploaded_files.items():
                        if file_info['visible']:
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.stl') as tmp_file:
                                tmp_file.write(file_info['data'])
                                tmp_path = tmp_file.name
                            try:
                                mesh = pv.read(tmp_path)
                                total_points += mesh.n_points
                            except:
                                pass
                            finally:
                                if os.path.exists(tmp_path):
                                    os.unlink(tmp_path)
                    st.metric("总点数", f"{total_points:,}")
                with col_stat3:
                    total_faces = 0
                    for file_id, file_info in st.session_state.uploaded_files.items():
                        if file_info['visible']:
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.stl') as tmp_file:
                                tmp_file.write(file_info['data'])
                                tmp_path = tmp_file.name
                            try:
                                mesh = pv.read(tmp_path)
                                total_faces += mesh.n_cells
                            except:
                                pass
                            finally:
                                if os.path.exists(tmp_path):
                                    os.unlink(tmp_path)
                    st.metric("总面数", f"{total_faces:,}")
            else:
                st.info("没有可见的文件，请至少选择一个文件显示")

    else:
        st.info("请上传一个或多个STL文件开始查看")

with col3:
    # 保存和分享功能
    st.subheader("保存与分享（建设中）")

    if st.session_state.uploaded_files:
        # 保存会话
        if st.button("💾 保存当前会话", use_container_width=True):
            session_json = save_session_state()
            st.download_button(
                label="📥 下载会话文件",
                data=session_json,
                file_name=f"stl_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

        st.markdown("---")

        # 加载会话
        st.subheader("加载会话（建设中）")
        uploaded_session = st.file_uploader(
            "上传会话文件",
            type=['json'],
            key="session_uploader"
        )

        if uploaded_session:
            try:
                session_json = uploaded_session.getvalue().decode('utf-8')
                if st.button("🔄 加载会话", use_container_width=True):
                    load_session_state(session_json)
            except Exception as e:
                st.error(f"读取会话文件失败: {str(e)}")

    ## # 部署指南
    ## st.markdown("---")
    ## st.subheader("🌐 部署到 GitHub")
##
    ## st.markdown("""
    ## 1. Fork [Streamlit模板仓库](https://github.com/streamlit/app-template)
    ## 2. 替换 `streamlit_app.py` 为此代码
    ## 3. 添加 `requirements.txt`:
    ## ```
    ## streamlit==1.32.0
    ## pyvista==0.43.0
    ## numpy==1.26.0
    ## stpyvista==0.0.6
    ## ```
    ## 4. 在GitHub设置中启用GitHub Pages
    ## """)

    # 生成分享链接
    if st.session_state.uploaded_files:
        st.markdown("---")
        st.subheader("🔗 快速分享（建设中）")
        st.info("保存会话文件后，可以发送给其他人加载查看")

# 页脚
st.markdown("---")
st.markdown(
    "使用 [Streamlit](https://streamlit.io), [PyVista](https://www.pyvista.org/) 和 [stpyvista](https://github.com/arnaudmiribel/stpyvista) 构建")


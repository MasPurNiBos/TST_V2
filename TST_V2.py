import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import time
import base64
import io
import re
from st_supabase_connection import SupabaseConnection

# ==========================================
# 1. CONFIG & THEME (WIDE MODE)
# ==========================================
st.set_page_config(
    page_title="TST V2 - Testing Issue Tracker",
    page_icon="assets/logo.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_base64_image(image_path):
    try:
        with open(image_path, "r", encoding="utf-8") as f:
            return base64.b64encode(f.read().encode("utf-8")).decode("utf-8")
    except:
        return ""

def render_header(icon_name, title, size=24):
    icon_b64 = get_base64_image(f"assets/{icon_name}")
    if icon_b64:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 10px;">
            <img src="data:image/svg+xml;base64,{icon_b64}" width="{size}" style="opacity: 0.9;">
            <span style="font-size: 20px; font-weight: 700; color: #FFFFFF;">{title}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"### {title}")

def get_wib_time():
    tz = pytz.timezone('Asia/Jakarta')
    return datetime.now(tz).strftime("%d/%m %H:%M")

def clean_sheet_name(name):
    clean = re.sub(r'[\[\]:*?/\\]', '', name)
    return clean[:31]

# ==========================================
# 3. DATABASE CONNECTION
# ==========================================
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except:
    st.error("Gagal konek Supabase. Cek secrets.toml")
    st.stop()

def login_user(username, password):
    try:
        response = conn.table("users").select("*").eq("username", username).eq("password", password).execute()
        if len(response.data) > 0:
            return response.data[0]
        return None
    except:
        return None

# ==========================================
# 4. SESSION STATE INIT
# ==========================================
if 'user' not in st.session_state: st.session_state.user = None
if 'active_ticket_id' not in st.session_state: st.session_state.active_ticket_id = None

# ==========================================
# 5. CSS STYLE (FULL DARK NAVY)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #0F172A;
    }

    h1, h2, h3, h4, h5, h6, .stMarkdown p, .stText, label, div[data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
    }

    .stCaption, span[data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #1E293B !important;
        color: white !important;
        border: 1px solid #334155 !important;
        border-radius: 6px !important;
    }

    div[data-testid="stMetric"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        padding: 15px;
        border-radius: 10px;
    }
    div[data-testid="stMetricValue"] { color: #F8FAFC !important; }

    .stButton button {
        background-color: #2563EB;
        color: white !important;
        font-weight: 600;
        border-radius: 6px;
        border: none;
        height: 42px;
    }
    .stButton button:hover { background-color: #1D4ED8; }

    .stButton button:disabled {
        background-color: #334155;
        color: #64748B !important;
        cursor: not-allowed;
    }

    div[data-testid="stDialog"] { background-color: #1E293B; }
    [data-testid="stDataFrame"] { border: 1px solid #334155; border-radius: 8px; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0);}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 6. MAIN APP FLOW
# ==========================================

# --- A. LOGIN PAGE ---
if st.session_state.user is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_left, c_center, c_right = st.columns([1, 1.2, 1])

    with c_center:
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center;'>🔐 TST Login</h1>", unsafe_allow_html=True)

            u = st.text_input("Username")
            p = st.text_input("Password", type="password")

            if st.button("Sign In", use_container_width=True):
                if u and p:
                    with st.spinner("Verifying..."):
                        user = login_user(u, p)
                        if user:
                            st.session_state.user = user
                            st.rerun()
                        else:
                            st.error("Invalid credentials")

# --- B. DASHBOARD APPLICATION ---
else:
    # FETCH DATA REALTIME
    proj_data = conn.table("projects").select("*").execute()
    projects_list = [p['name'] for p in proj_data.data] if proj_data.data else []

    issues_data = conn.table("issues").select("*").execute()
    all_issues = issues_data.data if issues_data.data else []

    # --- MODAL DETAIL ---
    @st.dialog("Issue Detail", width="large")
    def show_issue_detail(issue_id):
        res = conn.table("issues").select("*").eq("id", issue_id).execute()
        if not res.data:
            st.error("Issue not found.")
            return

        issue_data = res.data[0]

        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader(f"{issue_data['id']}")
            st.caption(f"{issue_data['description']}")
        with c2:
            if issue_data['status']: st.success("RESOLVED")
            else: st.error("OPEN")

        st.markdown("---")
        col_left, col_right = st.columns([1, 1.5])

        # EVIDENCE (DISABLED FOR NOW)
        with col_left:
            with st.container(border=True):
                render_header("Image.svg", "Evidence", size=20)
                # Tampilkan gambar kalau ada (manual DB insert), tapi upload dimatiin dulu
                existing_img = issue_data.get('evidence')
                if existing_img:
                    st.image(existing_img, caption="Evidence", use_container_width=True)
                else:
                    st.info("📷 Image upload feature: Not implemented yet.")

        # DISCUSSION (LIVE)
        with col_right:
            with st.container(border=True):
                render_header("Chat.svg", "Discussion", size=20)

                comments = issue_data.get('comments', [])
                if comments is None: comments = []

                chat_container = st.container(height=300)
                with chat_container:
                    if not comments: st.caption("No comments yet.")
                    for chat in comments:
                        with st.chat_message("user"):
                            st.markdown(f"**{chat['user']}** <span style='color:grey; font-size:10px;'>{chat['time']}</span>", unsafe_allow_html=True)
                            st.write(chat['msg'])

                c_in, c_btn = st.columns([4, 1], vertical_alignment="bottom")
                with c_in:
                    txt = st.text_input("Msg", key=f"txt_{issue_id}", label_visibility="collapsed", placeholder="Type comment...")
                with c_btn:
                    if st.button("Send", key=f"snd_{issue_id}", use_container_width=True):
                        if txt:
                            new_chat = {
                                "user": st.session_state.user['username'],
                                "msg": txt,
                                "time": get_wib_time()
                            }
                            comments.append(new_chat)
                            conn.table("issues").update({"comments": comments}).eq("id", issue_id).execute()
                            st.session_state.active_ticket_id = issue_id
                            st.rerun()

    # --- SIDEBAR ---
    with st.sidebar:
        render_header("Logo.svg", "TST v2", size=32)
        st.caption(f"Logged in as: {st.session_state.user.get('full_name', 'User')}")

        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        st.markdown("---")
        project_options = ["All Projects (Dashboard)"] + projects_list
        selected_nav = st.selectbox("Project", project_options, label_visibility="collapsed")

        # ADD PROJECT
        with st.popover("➕ Add Project", use_container_width=True):
            np = st.text_input("New Project Name")
            if st.button("Create Project"):
                if np and np not in projects_list:
                    conn.table("projects").insert({"name": np}).execute()
                    st.rerun()

        # DELETE PROJECT (NEW FEATURE)
        with st.popover("🗑️ Delete Project", use_container_width=True):
            st.warning("Hati-hati! Menghapus project tidak menghapus isunya (tapi hidden).")
            del_proj = st.selectbox("Select to Delete", ["-- Select --"] + projects_list)
            if st.button("Confirm Delete"):
                if del_proj != "-- Select --":
                    conn.table("projects").delete().eq("name", del_proj).execute()
                    st.toast(f"Project {del_proj} deleted!", icon="🗑️")
                    time.sleep(1)
                    st.rerun()

        st.markdown("---")
        # Export Logic
        if selected_nav != "All Projects (Dashboard)" and all_issues:
            df_all = pd.DataFrame(all_issues)
            if not df_all.empty:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                    df_all.to_excel(writer, index=False, sheet_name="Backup")
                st.download_button("Export Excel", data=buf, file_name="TST_Full.xlsx", use_container_width=True)
        else:
            st.button("Export Excel", disabled=True, use_container_width=True)

    # --- MAIN CONTENT ---
    if st.session_state.active_ticket_id:
        show_issue_detail(st.session_state.active_ticket_id)
        st.session_state.active_ticket_id = None

    if selected_nav == "All Projects (Dashboard)":
        render_header("Dashboard.svg", "Global Dashboard", size=28)
        filtered_issues = all_issues

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            with st.container(border=True): st.metric("Total Issues", len(filtered_issues))
        with m2:
            with st.container(border=True): st.metric("Pending", len([i for i in filtered_issues if not i['status']]))
        with m3:
            with st.container(border=True): st.metric("Resolved", len([i for i in filtered_issues if i['status']]))
        with m4:
            with st.container(border=True): st.metric("High Sev", len([i for i in filtered_issues if i['severity'] in ["High", "Critical"] and not i['status']]))

        st.write("")
        st.info("Select a project from the sidebar to manage issues.")

    else:
        # PROJECT VIEW
        filtered_issues = [i for i in all_issues if i['project'] == selected_nav]
        render_header("Project.svg", selected_nav, size=28)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", len(filtered_issues))
        c2.metric("Pending", len([i for i in filtered_issues if not i['status']]))
        c3.metric("Resolved", len([i for i in filtered_issues if i['status']]))
        c4.metric("High Sev", len([i for i in filtered_issues if i['severity'] in ["High", "Critical"] and not i['status']]))

        st.markdown("---")

        # QUICK ADD TO DB
        with st.container(border=True):
            render_header("Add.svg", "Quick Add Issue", size=20)
            c_desc, c_rem, c_sev, c_btn = st.columns([3, 2, 1, 1], gap="small")
            with c_desc: desc_in = st.text_input("Desc", label_visibility="collapsed", placeholder="Bug description...")
            with c_rem: rem_in = st.text_input("Rem", label_visibility="collapsed", placeholder="Expected...")
            with c_sev: sev_in = st.selectbox("Sev", ["Low", "Medium", "High", "Critical"], label_visibility="collapsed")
            with c_btn:
                if st.button("Add", use_container_width=True):
                    if desc_in:
                        new_id = f"#T-{len(all_issues)+1:03d}"
                        conn.table("issues").insert({
                            "id": new_id, "project": selected_nav, "description": desc_in, "remarks": rem_in,
                            "severity": sev_in, "status": False, "time_found": get_wib_time(), "time_resolved": "-",
                            "reporter": st.session_state.user['username'], "comments": []
                        }).execute()
                        st.rerun()

        st.write("")

        # TABLE EDIT TO DB
        if filtered_issues:
            render_header("ListTable.svg", "Issue Log", size=22)
            df = pd.DataFrame(filtered_issues)
            df['delete'] = False
            df = df.rename(columns={'description': 'desc'})
            df_display = df[['delete', 'status', 'id', 'time_found', 'desc', 'remarks', 'severity', 'time_resolved']]

            res = st.data_editor(
                df_display,
                column_config={
                    "delete": st.column_config.CheckboxColumn("Del", width="small"),
                    "status": st.column_config.CheckboxColumn("Done", width="small"),
                    "id": st.column_config.TextColumn("ID", width="small", disabled=True),
                    "desc": st.column_config.TextColumn("Description", width="large"),
                    "remarks": st.column_config.TextColumn("Remarks", width="medium"),
                    "time_found": st.column_config.TextColumn("Found", disabled=True, width="small"),
                    "time_resolved": st.column_config.TextColumn("Resolved", disabled=True, width="small"),
                },
                use_container_width=True,
                hide_index=True,
                key="editor"
            )

            if not res.equals(df_display):
                for index, row in res.iterrows():
                    issue_id = row['id']
                    orig_row = df_display[df_display['id'] == issue_id].iloc[0]

                    if row['delete']:
                        conn.table("issues").delete().eq("id", issue_id).execute()
                        st.rerun()
                        break

                    updates = {}
                    if row['desc'] != orig_row['desc']: updates['description'] = row['desc']
                    if row['remarks'] != orig_row['remarks']: updates['remarks'] = row['remarks']
                    if row['severity'] != orig_row['severity']: updates['severity'] = row['severity']
                    if row['status'] != orig_row['status']:
                        updates['status'] = row['status']
                        updates['time_resolved'] = get_wib_time() if row['status'] else "-"

                    if updates:
                        conn.table("issues").update(updates).eq("id", issue_id).execute()
                        st.rerun()

            st.write("")
            st.markdown("---")
            render_header("Detail.svg", "Details", size=20)
            opts = ["-- Select --"] + [f"{i['id']} - {i['description']}" for i in filtered_issues]
            sel = st.selectbox("Select", opts, label_visibility="collapsed")
            if st.button("View Detail", use_container_width=True, type="primary"):
                if sel != "-- Select --":
                    show_issue_detail(sel.split(" - ")[0])
        else:
            st.info("No issues yet.")
"""
app.py
------
New chat + saved chat history in the sidebar, chat bubbles, search box at the
bottom, and a download option under every answer.
Run: streamlit run app.py
"""
import base64
import html as _html
import json
import os
import re
import time
from datetime import datetime

import requests
import streamlit as st
from newsapi.newsapi_exception import NewsAPIException

from auth import _lock as auth_lock
from auth import chats_file, create_session, login, signup, verify_session
from langchain_config import (
    get_news_articles,
    llm_chain,
    summarize_articles,
)

st.set_page_config(
    page_title="Equity Research News Tool",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded",
)

NUM_ARTICLES = 10
SORT_BY = "relevancy"

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
@keyframes fadeUp  { from {opacity:0; transform:translateY(16px);} to {opacity:1; transform:none;} }
@keyframes slideIn { from {opacity:0; transform:translateX(-16px);} to {opacity:1; transform:none;} }
@keyframes floaty  { 0%,100%{transform:translateY(0);} 50%{transform:translateY(-12px);} }
@keyframes eyeblink{ 0%,92%,100%{transform:scaleY(1);} 96%{transform:scaleY(.1);} }
@keyframes spin    { to {transform:rotate(360deg);} }
@keyframes shimmer { 0%{background-position:-500px 0;} 100%{background-position:500px 0;} }
@keyframes bounce  { 0%,80%,100%{transform:translateY(0);opacity:.5;} 40%{transform:translateY(-6px);opacity:1;} }

:root { --g1:#E062C4; --g2:#7A6CF0; --grey:#EFEFF1; --mute:#8B8B96; --ink:#1D1D24; }
html, body, [data-testid="stApp"], .stMarkdown, button, input, textarea { font-family:'Plus Jakarta Sans', sans-serif !important; }
[data-testid="stApp"] { color:var(--ink); }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stAppDeployButton"] { display:none; }
.block-container, [data-testid="stMainBlockContainer"] { max-width:704px !important; padding-top:1.2rem !important; }
footer { visibility:hidden; }

/* hidden helper that sets / clears the login cookie */
.st-key-cookie_js { position:absolute; width:1px; height:1px; overflow:hidden; opacity:0; pointer-events:none; }

/* round grey menu button (the sidebar toggle) */
[data-testid="stSidebarCollapsedControl"] button, [data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] button { background:var(--grey); border-radius:50%; width:42px; height:42px; }

/* Sidebar = home screen: profile, gradient button, recent queries */
[data-testid="stSidebar"] { background:#fff; border-right:0; box-shadow:0 0 40px rgba(0,0,0,.08); }
[data-testid="stSidebar"] > div { animation: slideIn .5s ease both; }
[data-testid="stSidebar"] .stElementContainer:has(.stButton), [data-testid="stSidebar"] .stButton { width:100% !important; }
[data-testid="stSidebar"] .st-key-new_chat button > div, [data-testid="stSidebar"] [class*="st-key-chat_"] button > div { flex:1; justify-content:flex-start !important; text-align:left; }
.prof { display:flex; align-items:center; gap:12px; margin:.2rem 0 1.1rem 0; }
.av { width:50px; height:50px; border-radius:50%; flex:none; background:linear-gradient(135deg,#9d8cf5,#e9a2d6);
      color:#fff; font-weight:700; font-size:18px; display:grid; place-items:center; }
.prof small { display:block; color:var(--mute); font-size:.85rem; line-height:1.2; }
.prof b { font-size:1.15rem; font-weight:600; }
.side-title { font-size:1.15rem; font-weight:500; margin:1.3rem 0 .6rem 0; }

[data-testid="stSidebar"] .st-key-new_chat button { width:100%; height:56px; border:0; border-radius:999px; color:#fff;
    background:linear-gradient(90deg,#e873c8,#8f7cf0); justify-content:space-between; padding:0 8px 0 24px;
    box-shadow:0 12px 26px rgba(138,108,240,.35); transition:transform .2s ease; }
[data-testid="stSidebar"] .st-key-new_chat button:hover { transform:translateY(-2px); color:#fff; }
[data-testid="stSidebar"] .st-key-new_chat button p { color:#fff; font-weight:600; }
[data-testid="stSidebar"] .st-key-new_chat button::after { content:"\\2192"; width:42px; height:42px; border-radius:50%; background:rgba(255,255,255,.28);
    display:grid; place-items:center; font-size:1.25rem; }

[data-testid="stSidebar"] [class*="st-key-chat_"] button { width:100%; display:flex; justify-content:flex-start; gap:12px; text-align:left;
    background:var(--grey); border:1.5px solid transparent; border-radius:10px; padding:.5rem .7rem; box-shadow:none; }
[data-testid="stSidebar"] [class*="st-key-chat_"] button::before { content:var(--ini,"V"); flex:none; width:34px; height:34px; border-radius:50%;
    background:linear-gradient(135deg,#9d8cf5,#e9a2d6); color:#fff; display:grid; place-items:center; font-size:.8rem; font-weight:700; }
[data-testid="stSidebar"] [class*="st-key-chat_"] button p { display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
    font-size:.92rem; font-weight:500; text-align:left; }
[data-testid="stSidebar"] [class*="st-key-chat_"] button:hover { border-color:var(--g2); }
[data-testid="stSidebar"] [class*="st-key-chat_"] button[kind="primary"], [data-testid="stSidebar"] [class*="st-key-chat_"] [data-testid="stBaseButton-primary"] {
    background:#fff; border-color:var(--g2); color:var(--ink); }

/* Pill buttons (downloads, clear history, log out) */
.stButton > button, .stDownloadButton > button { border-radius:999px; font-weight:500; border:1px solid #d9d9df; background:#fff;
    box-shadow:none; transition:border-color .2s ease, color .2s ease; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color:var(--g2); color:var(--g2); }

/* Download .md / .txt sit close together (columns shrink to the button width) */
[data-testid="stHorizontalBlock"]:has(.stDownloadButton) { gap:.5rem !important; flex-wrap:nowrap; }
[data-testid="stHorizontalBlock"]:has(.stDownloadButton) > [data-testid="stColumn"],
[data-testid="stHorizontalBlock"]:has(.stDownloadButton) > [data-testid="column"] { flex:0 0 auto !important; width:auto !important; min-width:0 !important; }

/* Top bar and empty chat screen */
.topbar { display:flex; align-items:center; gap:12px; margin:0 0 .6rem 0; padding-left:54px; }
.topbar .ttl { flex:1; text-align:center; font-size:1.5rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.empty { display:flex; flex-direction:column; align-items:center; text-align:center; padding-top:2vh; animation: fadeUp .6s ease both; }
.empty .bot { width:190px; animation: floaty 3.4s ease-in-out infinite; }
.empty .eye { transform-box:fill-box; transform-origin:center; animation: eyeblink 4s infinite; }
.empty p { margin:.8rem 0 0 0; font-size:1.05rem; }
.empty .big { font-size:1.7rem; font-weight:500; line-height:1.3; }

/* Messages: grey bubble for you, plain text with a small bot icon for the answer */
[data-testid="stChatMessage"] { background:transparent; border-radius:0; padding:.4rem 0; gap:.75rem; animation: fadeUp .45s ease both; }
[data-testid="stChatMessageAvatarUser"] { display:none; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { justify-content:flex-end; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
    flex:0 1 auto; max-width:88%; margin:0 0 0 auto; background:var(--grey); border-radius:14px; padding:.6rem .9rem; }
[data-testid="stChatMessageAvatarAssistant"] { width:26px; height:26px; min-width:26px; flex:none; font-size:0; color:transparent;
    background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%237a6cf0' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='6' width='18' height='12' rx='4'/%3E%3Cpath d='M9 11v2M15 11v2M12 6V3M19 2v3M17.5 3.5h3'/%3E%3C/svg%3E") center/26px no-repeat !important; }
[data-testid="stChatMessageAvatarAssistant"] > * { display:none; }
[data-testid="stChatMessage"] h3 { font-size:1rem; font-weight:700; padding:.7rem 0 .2rem 0; margin:0; }
[data-testid="stChatMessage"] h3:first-child { padding-top:0; }

/* Search box */
[data-testid="stBottom"] > div { background:#fff; }
[data-testid="stChatInput"] { border-radius:20px; }
[data-testid="stChatInput"] > div { background:var(--grey); border:0; border-radius:20px; }
[data-testid="stChatInput"] textarea { background:transparent; }
[data-testid="stChatInputSubmitButton"] { background:linear-gradient(135deg,var(--g1),var(--g2)) !important; color:#fff !important; border-radius:50%; }

/* Loader */
.loader { padding:1rem 1.2rem; border-radius:14px; background:var(--grey); animation: fadeUp .4s ease both; }
.loader .row { display:flex; align-items:center; gap:.9rem; font-weight:600; }
.spinner { width:22px; height:22px; border-radius:50%; border:3px solid rgba(122,108,240,.25); border-top-color:var(--g2); animation: spin .9s linear infinite; }
.loader .dots { animation: bounce 1.2s infinite; display:inline-block; }
.skeleton { height:12px; border-radius:6px; margin-top:.7rem;
    background: linear-gradient(90deg, rgba(128,128,128,.12) 25%, rgba(128,128,128,.28) 37%, rgba(128,128,128,.12) 63%);
    background-size:500px 100%; animation: shimmer 1.4s infinite linear; }

@media (prefers-reduced-motion: reduce) { * { animation:none !important; transition:none !important; } }
</style>
""",
    unsafe_allow_html=True,
)

st.session_state.setdefault("user", None)

if "cookie_checked" not in st.session_state:
    st.session_state.cookie_checked = True
    try:
        st.session_state.user = verify_session(st.context.cookies.get("session"))
    except Exception:
        pass


def run_js(code):
    doc = f"<script>{code}</script>"
    with st.container(key="cookie_js"):
        if hasattr(st, "iframe"):
            st.iframe(doc, height=1)
        else:  # older Streamlit
            import streamlit.components.v1 as components
            components.html(doc, height=0)


COOKIE_AGE = 7 * 24 * 3600


BG_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--blur:5px;--accent:#d62828}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;height:100%;overflow:hidden}
.stage{position:fixed;inset:0;overflow:hidden;background:linear-gradient(135deg,#d6e6f7 0%,#eef3f8 50%,#f8e4dc 100%);isolation:isolate}
.base{position:absolute;inset:0;overflow:hidden;filter:blur(var(--blur));opacity:.55;z-index:-3}
.words{position:absolute;left:0;top:0;width:2600px;height:1700px;display:flex;flex-wrap:wrap;align-content:flex-start;font-family:Oswald,'Arial Narrow',sans-serif;text-transform:uppercase;line-height:.95;will-change:transform}
.words span{display:inline-block;margin:1px 7px}
.words .v{writing-mode:vertical-rl}
.wash{position:absolute;inset:0;z-index:-2;background:radial-gradient(70% 60% at 50% 50%,rgba(255,255,255,.55),transparent 75%)}
.lens{position:absolute;left:0;top:0;z-index:-1;will-change:transform}
.glass{position:absolute;left:0;top:0;border-radius:50%;overflow:hidden;background:radial-gradient(circle at 50% 45%,#f4fbff 0%,#dcecf6 100%);box-shadow:inset 0 0 0 6px #cfd4d9,inset 0 0 0 9px #8d949b,0 18px 40px rgba(20,40,70,.28)}
.glass .zoom{position:absolute;left:0;top:0;transform-origin:0 0;will-change:transform}
.glass .words{opacity:.9}
.glass::after{content:"";position:absolute;inset:0;border-radius:50%;background:linear-gradient(135deg,rgba(255,255,255,.55) 0%,transparent 38%)}
.focus{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font:600 var(--fs,60px)/1 Oswald,'Arial Narrow',sans-serif;color:var(--accent);text-transform:uppercase;text-shadow:0 0 14px #fff,0 0 4px #fff;z-index:2;white-space:nowrap}
.handle{position:absolute;height:34px;border-radius:18px;background:linear-gradient(180deg,#555 0%,#111 50%,#000 100%);transform-origin:0 50%;box-shadow:0 8px 16px rgba(0,0,0,.3)}
</style></head><body>
<div class="stage">
  <div class="base"><div class="words" id="w1"></div></div>
  <div class="wash"></div>
  <div class="lens" id="lens">
    <div class="handle" id="handle"></div>
    <div class="glass" id="glass"><div class="zoom" id="zoom"><div class="words" id="w2"></div></div><div class="focus" id="focus">Research</div></div>
  </div>
</div>
<script>
var WORDS=["research","knowledge","science","experiment","probe","examine","scan","think","project","mission","teaching","education","study","analysis","method","proof","wisdom","book","source","practice","facts","link","check","learning","discovery","ask","engine","stock","theory","data","insight","review"];
var seed=11;function r(){seed=(seed*16807)%2147483647;return (seed-1)/2147483646}
var w1=document.getElementById("w1"),w2=document.getElementById("w2"),html="";
for(var i=0;i<900;i++){
  var fs=Math.round(13+Math.pow(r(),2.2)*82),g=Math.round(40+r()*70),wt=r()>.55?600:400,v=r()>.88?"v":"";
  html+='<span class="'+v+'" style="font-size:'+fs+'px;font-weight:'+wt+';color:rgb('+g+','+(g+8)+','+(g+18)+')">'+WORDS[Math.floor(r()*WORDS.length)]+'</span>';
}
w1.innerHTML=html;w2.innerHTML=html;
var lens=document.getElementById("lens"),glass=document.getElementById("glass"),zoom=document.getElementById("zoom"),handle=document.getElementById("handle"),focus=document.getElementById("focus");
var S=1.28,R=0,still=matchMedia("(prefers-reduced-motion: reduce)").matches;
function size(){
  R=Math.max(120,Math.min(250,Math.min(innerWidth,innerHeight)*.27));
  glass.style.width=glass.style.height=(2*R)+"px";
  handle.style.width=(R*.75)+"px";handle.style.left=(R+R*.707+R*.02)+"px";handle.style.top=(R+R*.707-17)+"px";handle.style.transform="rotate(45deg)";
  handle.style.zIndex=0;focus.style.setProperty("--fs",(R*.4)+"px");
}
size();addEventListener("resize",size);
function frame(ms){
  var t=ms/1000,vw=innerWidth,vh=innerHeight;
  var dx=-220+70*Math.sin(t*.07),dy=-160+55*Math.cos(t*.055),T="translate3d("+dx+"px,"+dy+"px,0)";
  w1.style.transform=T;w2.style.transform=T;
  var cx=vw/2+vw*.27*Math.sin(t*.28),cy=vh/2+vh*.22*Math.sin(t*.41+1.2);
  lens.style.transform="translate3d("+(cx-R)+"px,"+(cy-R)+"px,0)";
  zoom.style.transform="translate("+R+"px,"+R+"px) scale("+S+") translate("+(-R)+"px,"+(-R)+"px) translate("+(-(cx-R))+"px,"+(-(cy-R))+"px)";
  if(!still)requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
</script></body></html>"""


AUTH_CSS = """
<style>
[data-testid="stApp"] { background: linear-gradient(135deg,#d6e6f7 0%,#eef3f8 50%,#f8e4dc 100%); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], [data-testid="stAppDeployButton"], [data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
.block-container, [data-testid="stMainBlockContainer"] { max-width: 420px !important;
        padding-top: max(2rem, 14vh) !important; position: relative; z-index: 1; }

/* the word-collage iframe fills the whole screen, behind the form */
.st-key-bg { position: fixed; inset: 0; z-index: -1; pointer-events: none; }
.st-key-bg iframe { position: fixed !important; inset: 0 !important; width: 100vw !important; height: 100vh !important; border: 0 !important; }

/* the plain white login card */
[class*="st-key-card_"] { position: relative; z-index: 3; background:#fff; border-radius:8px;
        padding:1.7rem 1.7rem 1.2rem 1.7rem; box-shadow:0 12px 40px rgba(20,40,70,.28); }
[class*="st-key-card_"] label, [class*="st-key-card_"] label p, [class*="st-key-card_"] .ct { color:#222 !important; }
[class*="st-key-card_"] .ct { margin:0 0 1rem 0 !important; padding:0 !important; font-size:1.5rem; font-weight:700; }
[data-testid="stForm"] { border:0 !important; padding:0 !important; background:transparent !important; box-shadow:none !important; }

[data-testid="stTextInput"] input { background:#fff !important; color:#222 !important; border:0 !important; }
[data-baseweb="input"], [data-baseweb="base-input"] { background:#fff !important; border-radius:6px !important; }
[data-baseweb="input"] { border:1px solid #bbb !important; }
[data-baseweb="input"]:focus-within { border-color:#1a56db !important; box-shadow:0 0 0 2px rgba(26,86,219,.25) !important; }
[data-testid="stTextInput"] button { color:#555 !important; }

.stElementContainer:has(.stFormSubmitButton), .stElementContainer:has(.stFormSubmitButton) > div, .stFormSubmitButton { width:100% !important; }
.stFormSubmitButton > button { width:100%; background:#222 !important; border:0 !important; border-radius:6px !important;
        color:#fff !important; padding:.6rem 1rem; transform:none !important; box-shadow:none !important; }
.stFormSubmitButton > button p { color:#fff !important; }

/* "New here? / Already have an account?" link buttons */
[class*="st-key-to_"] button { width:100%; background:transparent !important; border:0 !important; box-shadow:none !important;
        padding:.2rem 0 !important; transform:none !important; }
[class*="st-key-to_"] button p { color:#1a56db !important; text-decoration:underline; font-size:.9rem; font-weight:500; }
</style>
"""

LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs><linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6366F1"/><stop offset="1" stop-color="#EC4899"/></linearGradient></defs><style>.s1,.s2{transform-box:fill-box;transform-origin:center;animation:tw 2.4s ease-in-out infinite}.s2{animation-delay:1.2s}@keyframes tw{0%,100%{transform:scale(.75);opacity:.7}50%{transform:scale(1.15);opacity:1}}</style><rect width="64" height="64" rx="18" fill="url(#b)"/><path d="M43 21h3a4 4 0 0 1 4 4v21a4 4 0 0 1-4 4h-3z" fill="#fff" fill-opacity=".5"/><rect x="12" y="15" width="31" height="35" rx="4.5" fill="#fff"/><rect x="16" y="20" width="23" height="4.5" rx="2.2" fill="#4F46E5"/><rect x="16" y="28" width="10" height="9" rx="2" fill="#C7D2FE"/><rect x="29" y="28" width="10" height="2.5" rx="1.25" fill="#9CA3AF"/><rect x="29" y="33" width="10" height="2.5" rx="1.25" fill="#9CA3AF"/><rect x="16" y="40" width="23" height="2.5" rx="1.25" fill="#9CA3AF"/><rect x="16" y="44.5" width="15" height="2.5" rx="1.25" fill="#9CA3AF"/><path class="s1" d="M47 7l2.4 6.2L55.6 15.6l-6.2 2.4L47 24.2l-2.4-6.2L38.4 15.6l6.2-2.4z" fill="#FDE68A"/><path class="s2" d="M54 27.5l1.2 3.1 3.1 1.2-3.1 1.2-1.2 3.1-1.2-3.1-3.1-1.2 3.1-1.2z" fill="#fff"/></svg>'
)


def _logo_img():
    """The News + AI logo (a newspaper with AI sparkles) as an image data URI."""
    return "data:image/svg+xml;base64," + base64.b64encode(LOGO_SVG.encode()).decode()



def set_view(view):
    st.session_state.auth_view = view


def render_login():
    with st.container(key="card_login"):
        st.markdown('<h2 class="ct">Log in</h2>', unsafe_allow_html=True)
        banner = st.empty()
        if st.session_state.pop("signup_done", None):
            banner.success("Account created. You can log in now.")
        with st.form("login_form"):
            u = st.text_input("Username", key="login_user")
            p = st.text_input("Password", type="password", key="login_pass")
            go = st.form_submit_button("Log in", type="primary")
        if go:
            with auth_lock:
                ok, msg = login(u, p)
            if ok:
                st.session_state.user = u.strip().lower()
                st.session_state.cookie_to_set = create_session(st.session_state.user)
                st.rerun()
            st.error(msg)
        st.button("New here? Create an account", key="to_signup", on_click=set_view, args=("signup",))


def render_signup():
    with st.container(key="card_signup"):
        st.markdown('<h2 class="ct">Create account</h2>', unsafe_allow_html=True)
        with st.form("signup_form"):
            u2 = st.text_input("Username", key="signup_user", help="3-20 letters, numbers or _")
            p2 = st.text_input("Password", type="password", key="signup_pass", help="At least 8 characters")
            c2 = st.text_input("Confirm password", type="password", key="signup_confirm")
            code = st.text_input("Invite code", type="password", key="signup_code") if os.getenv("SIGNUP_CODE") else ""
            go2 = st.form_submit_button("Create account", type="primary")
        if go2:
            with auth_lock:
                ok, msg = signup(u2, p2, c2, code)
            if ok:
                st.session_state.login_user = u2.strip().lower()
                st.session_state.signup_done = True
                st.session_state.auth_view = "login"
                st.rerun()
            st.error(msg)
        st.button("Already have an account? Log in", key="to_login", on_click=set_view, args=("login",))


def render_auth():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    if st.session_state.pop("clear_cookie", None):
        run_js("document.cookie='session=; path=/; max-age=0';try{window.parent.document.cookie='session=; path=/; max-age=0'}catch(e){}")
    with st.container(key="bg"):
        if hasattr(st, "iframe"):  # newer Streamlit
            st.iframe(BG_HTML, height=600)
        else:  # older Streamlit
            import streamlit.components.v1 as components
            components.html(BG_HTML, height=600)
    if st.session_state.get("auth_view", "login") == "signup":
        render_signup()
    else:
        render_login()


if not st.session_state.user:
    render_auth()
    st.stop()

USER = st.session_state.user
if st.session_state.get("cookie_to_set"):
    _tok = st.session_state.pop("cookie_to_set")
    run_js(f"var c='session={_tok}; path=/; max-age={COOKIE_AGE}; SameSite=Lax';try{{window.parent.document.cookie=c}}catch(e){{document.cookie=c}}")
st.markdown(
    f"<style>[data-testid='stApp']{{--ini:'{USER[:1].upper()}'}}</style>",
    unsafe_allow_html=True,
)


def greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning", "☀️"
    if 12 <= hour < 17:
        return "Good afternoon", "🌤️"
    if 17 <= hour < 21:
        return "Good evening", "🌆"
    return "Good night", "🌙"


def logout():
    for key in ("user", "chats", "order", "current"):
        st.session_state.pop(key, None)
    st.session_state.clear_cookie = True  # the login page removes the cookie


def load_chats():
    try:
        data = json.loads(chats_file(USER).read_text(encoding="utf-8"))
        return data.get("chats", {}), data.get("order", [])
    except Exception:
        return {}, []


def save_chats():
    try:
        f = chats_file(USER)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(
            json.dumps({"chats": st.session_state.chats, "order": st.session_state.order}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


if "chats" not in st.session_state:
    chats, order = load_chats()
    st.session_state.chats = chats
    st.session_state.order = order
    st.session_state.current = None


def new_chat():
    st.session_state.current = None


def open_chat(chat_id):
    st.session_state.current = chat_id


def clear_all():
    st.session_state.chats, st.session_state.order, st.session_state.current = {}, [], None
    save_chats()


def esc(text):
    return (text or "").replace("$", "\\$")


def loader_html(step_text):
    return (
        f'<div class="loader"><div class="row"><div class="spinner"></div>'
        f'<div>{step_text}<span class="dots"> ...</span></div></div>'
        f'<div class="skeleton" style="width:92%"></div>'
        f'<div class="skeleton" style="width:78%"></div>'
        f'<div class="skeleton" style="width:85%"></div></div>'
    )


def friendly_error(e):
    msg = str(e)
    low = msg.lower()
    if isinstance(e, NewsAPIException):
        code = e.get_code()
        if code in ("apiKeyInvalid", "apiKeyMissing", "apiKeyDisabled", "apiKeyExhausted"):
            return "🔑 Your **NewsAPI key** is missing or invalid. Check `NEWSAPI_KEY` in your `.env` file."
        if code in ("rateLimited", "maximumResultsReached"):
            return "⏳ **NewsAPI limit reached** (the free plan allows 100 requests/day). Try again later."
        return f"📰 NewsAPI error: {e.get_message()}"
    if isinstance(e, requests.exceptions.ConnectionError) or "connection error" in low or "connecterror" in low:
        return "🌐 **No internet connection** (or the server is unreachable). Check your network and try again."
    if "401" in low or "invalid_api_key" in low or "invalid api key" in low:
        return "🔑 Your **LLM API key** is invalid. Check the key in your `.env` file."
    if "model_not_found" in low or "404" in low:
        return ("🤖 The **model name** was not found. Run `python list_groq_models.py` "
                "and update `GROQ_MODEL` in your `.env` file.")
    if "429" in low or "rate limit" in low or "rate_limit" in low:
        return "⏳ **LLM rate limit reached.** Please wait a minute and try again."
    return f"Something went wrong: {msg}"


# Caching: the same query is not fetched/summarized again for 1 hour,
# which also protects the free NewsAPI limit (100 requests/day).
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_articles(query, page_size, sort_by):
    return get_news_articles(query, page_size=page_size, sort_by=sort_by)


@st.cache_data(ttl=3600, show_spinner=False)
def generate_summary(query, summaries):
    return llm_chain.run({"query": query, "summaries": summaries})


def run_search(query):
    start = time.time()
    loader = st.empty()
    try:
        loader.markdown(loader_html("📰 Fetching the latest news"), unsafe_allow_html=True)
        articles = fetch_articles(query, NUM_ARTICLES, SORT_BY)
        if not articles:
            loader.empty()
            st.warning("No articles found for this query. Try different keywords.")
            return None

        loader.markdown(loader_html(f"🧠 Summarizing {len(articles)} articles with AI"), unsafe_allow_html=True)
        summaries = summarize_articles(articles)
        if not summaries:
            loader.empty()
            st.warning("The articles found had no description text to summarize.")
            return None
        summary = generate_summary(query, summaries)
    except Exception as e:
        loader.empty()
        st.error(friendly_error(e))
        return None

    loader.empty()
    sources = {(a.get("source") or {}).get("name") for a in articles}
    sources_text = "\n".join(
        f"- {a.get('title', '')} ({(a.get('source') or {}).get('name', '')}) - {a.get('url', '')}"
        for a in articles
    )
    return {
        "query": query,
        "summary": summary,
        "n_articles": len(articles),
        "n_sources": len(sources),
        "elapsed": round(time.time() - start, 1),
        "export": f"# {query}\n\n{summary}\n\n## Sources\n{sources_text}\n",
    }


def render_answer(turn, key):
    st.markdown(esc(turn["summary"]))
    slug = re.sub(r"\W+", "_", turn["query"]).strip("_")[:30] or "news_summary"
    c1, c2, _ = st.columns([1.5, 1.5, 2])
    c1.download_button("Download .md", turn["export"], file_name=f"{slug}.md",
                       mime="text/markdown", key=f"dl_md_{key}")
    c2.download_button("Download .txt", turn["export"], file_name=f"{slug}.txt",
                       mime="text/plain", key=f"dl_txt_{key}")


prompt = st.chat_input("Search a company, index or topic...")
q = (prompt or "").strip()

current_id = st.session_state.current
chat = st.session_state.chats.get(current_id)
turns = chat["turns"] if chat else []

topbar = st.empty()


def draw_topbar():
    c = st.session_state.chats.get(st.session_state.current)
    title_text = _html.escape(c["title"]) if c else "New Chat"
    topbar.markdown(
        f'<div class="topbar"><div class="ttl">{title_text}</div><span class="av">{USER[:1].upper()}</span></div>',
        unsafe_allow_html=True,
    )


draw_topbar()

if not turns and not q:
    greet, _icon = greeting()
    st.markdown(
        f"""
        <div class="empty">
            <svg class="bot" viewBox="0 0 200 230" aria-hidden="true"><defs><linearGradient id="bg1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#eaf3ff"/><stop offset="1" stop-color="#f3cfe8"/></linearGradient></defs><ellipse cx="100" cy="218" rx="52" ry="8" fill="#000" opacity=".08"/><line x1="132" y1="32" x2="146" y2="16" stroke="#c7b6ee" stroke-width="4" stroke-linecap="round"/><circle cx="148" cy="13" r="5" fill="#f2a6d8"/><rect x="55" y="108" width="90" height="88" rx="38" fill="url(#bg1)"/><circle cx="50" cy="142" r="15" fill="url(#bg1)"/><circle cx="150" cy="142" r="15" fill="url(#bg1)"/><rect x="40" y="28" width="120" height="92" rx="44" fill="url(#bg1)"/><rect x="54" y="46" width="92" height="58" rx="27" fill="#15224a"/><circle class="eye" cx="80" cy="75" r="12" fill="none" stroke="#2fe0ff" stroke-width="5"/><circle class="eye" cx="120" cy="75" r="12" fill="none" stroke="#2fe0ff" stroke-width="5"/><path d="M90 93q10 7 20 0" stroke="#7fe8ff" stroke-width="3" fill="none" stroke-linecap="round"/></svg>
            <p>{greet}, {USER}</p>
            <div class="big">How can I help you?</div>
            <p style="color:#8B8B96;font-size:.95rem">Enter a company, index or topic to get the latest news articles summarized.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

for i, turn in enumerate(turns):
    with st.chat_message("user"):
        st.markdown(esc(turn["query"]))
    with st.chat_message("assistant"):
        render_answer(turn, f"{current_id}_{i}")

if q:
    with st.chat_message("user"):
        st.markdown(esc(q))
    with st.chat_message("assistant"):
        turn = run_search(q)
        if turn:
            if st.session_state.current is None:  # first message of a new chat
                chat_id = str(int(time.time() * 1000))
                st.session_state.chats[chat_id] = {
                    "title": q[:60],
                    "time": datetime.now().strftime("%d %b, %H:%M"),
                    "turns": [],
                }
                st.session_state.order.insert(0, chat_id)
                st.session_state.current = chat_id
            chat_id = st.session_state.current
            st.session_state.chats[chat_id]["turns"].append(turn)
            save_chats()
            st.session_state.just_answered = True
            st.rerun()

if st.session_state.pop("just_answered", False):
    st.toast("Summary is ready!", icon="✅")

draw_topbar()

with st.sidebar:
    st.markdown(
        f'<div class="prof"><span class="av">{USER[:1].upper()}</span>'
        f'<div><small>Hi {USER}</small><b>Welcome Back</b></div></div>',
        unsafe_allow_html=True,
    )
    st.button("Start new chat", key="new_chat", on_click=new_chat)
    st.markdown('<div class="side-title">Recent Queries</div>', unsafe_allow_html=True)
    if st.session_state.order:
        for cid in st.session_state.order[:30]:
            item = st.session_state.chats[cid]
            label = item["title"]
            st.button(label if len(label) <= 60 else label[:59] + "…", key=f"chat_{cid}",
                      on_click=open_chat, args=(cid,),
                      type="primary" if cid == st.session_state.current else "secondary")
        st.divider()
        st.button("Clear all history", key="clear_all", on_click=clear_all)
    else:
        st.caption("No chats yet. Your searches will show up here.")
    st.divider()
    st.caption(f"Signed in as **{USER}**")
    st.button("Log out", key="logout", on_click=logout)
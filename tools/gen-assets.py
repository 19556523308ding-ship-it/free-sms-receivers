#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMS Hub 素材库生成器
====================
按「设计资源库」蓝图（12 个分区）批量生成 SVG 素材。

设计令牌严格对齐设计文档 §41-§43：
  bg      #070B12   surface #101722   surface-2 #16202E
  primary #4F7FFF   accent  #2DD4A8
  success #22C55E   warning #F59E0B   muted-status #64748B
  text    #F8FAFC   muted   #94A3B8   dim #64748B
  border  rgba(255,255,255,.08)

用法：
  python tools/gen-assets.py [输出目录]
默认输出到 web/assets/
"""

import os
import sys
import math
import random

# ----------------------------------------------------------------------------
# 设计令牌
# ----------------------------------------------------------------------------
BG = "#070B12"
SURFACE = "#101722"
SURFACE2 = "#16202E"
PRIMARY = "#4F7FFF"
PRIMARY_HOVER = "#6B94FF"
ACCENT = "#2DD4A8"
SUCCESS = "#22C55E"
WARNING = "#F59E0B"
MUTED_STATUS = "#64748B"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
DIM = "#64748B"
BORDER = "rgba(255,255,255,.08)"

FONT = "Inter, PingFang SC, Microsoft YaHei, system-ui, sans-serif"

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "assets"
)

_written = []


def write(rel, content):
    """写入文件并记录"""
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content.strip() + "\n")
    _written.append(rel)


def svg(w, h, body, extra=""):
    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" xmlns="http://www.w3.org/2000/svg"{extra}>
{body}
</svg>'''


# ============================================================================
# 01 · 品牌 Logo
# ============================================================================
def gen_brand():
    # 图形标：手机 + 气泡
    mark = f'''  <rect x="10" y="6" width="34" height="52" rx="10" fill="url(#gPrimary)"/>
  <rect x="15" y="11" width="24" height="42" rx="7" fill="{BG}"/>
  <path d="M25 18H44C48.4183 18 52 21.5817 52 26V36C52 40.4183 48.4183 44 44 44H37L31 50V44H25C20.5817 44 17 40.4183 17 36V26C17 21.5817 20.5817 18 25 18Z" fill="url(#gAccent)"/>
  <circle cx="27" cy="31" r="2.2" fill="{BG}"/>
  <circle cx="34.5" cy="31" r="2.2" fill="{BG}"/>
  <circle cx="42" cy="31" r="2.2" fill="{BG}"/>'''

    defs = f'''  <defs>
    <linearGradient id="gPrimary" x1="10" y1="6" x2="44" y2="58" gradientUnits="userSpaceOnUse">
      <stop stop-color="{PRIMARY_HOVER}"/><stop offset="1" stop-color="{PRIMARY}"/>
    </linearGradient>
    <linearGradient id="gAccent" x1="17" y1="18" x2="52" y2="50" gradientUnits="userSpaceOnUse">
      <stop stop-color="{ACCENT}"/><stop offset="1" stop-color="#1FB894"/>
    </linearGradient>
  </defs>'''

    write("brand/logo-mark.svg", svg(64, 64, defs + "\n" + mark))

    write("brand/favicon.svg", svg(64, 64, f'''  <rect width="64" height="64" rx="16" fill="#081018"/>
{defs}
{mark}'''))

    write("brand/logo.svg", svg(280, 64, f'''{defs}
{mark}
  <text x="70" y="32" fill="{TEXT}" font-size="24" font-weight="700" font-family="{FONT}">SMS Hub</text>
  <text x="70" y="50" fill="{MUTED}" font-size="12.5" font-family="{FONT}">免费在线接码</text>'''))

    # 反白版（深色背景以外的场景）
    write("brand/logo-light.svg", svg(280, 64, f'''{defs}
  <rect x="10" y="6" width="34" height="52" rx="10" fill="{PRIMARY}"/>
  <rect x="15" y="11" width="24" height="42" rx="7" fill="#FFFFFF"/>
  <path d="M25 18H44C48.4183 18 52 21.5817 52 26V36C52 40.4183 48.4183 44 44 44H37L31 50V44H25C20.5817 44 17 40.4183 17 36V26C17 21.5817 20.5817 18 25 18Z" fill="{ACCENT}"/>
  <circle cx="27" cy="31" r="2.2" fill="#FFFFFF"/>
  <circle cx="34.5" cy="31" r="2.2" fill="#FFFFFF"/>
  <circle cx="42" cy="31" r="2.2" fill="#FFFFFF"/>
  <text x="70" y="32" fill="#0B1220" font-size="24" font-weight="700" font-family="{FONT}">SMS Hub</text>
  <text x="70" y="50" fill="#475569" font-size="12.5" font-family="{FONT}">免费在线接码</text>'''))

    # 单色标（用于 favicon 兜底 / 水印）
    write("brand/logo-mono.svg", svg(280, 64, f'''  <rect x="10" y="6" width="34" height="52" rx="10" fill="{MUTED}"/>
  <rect x="15" y="11" width="24" height="42" rx="7" fill="{BG}"/>
  <path d="M25 18H44C48.4183 18 52 21.5817 52 26V36C52 40.4183 48.4183 44 44 44H37L31 50V44H25C20.5817 44 17 40.4183 17 36V26C17 21.5817 20.5817 18 25 18Z" fill="{TEXT}"/>
  <circle cx="27" cy="31" r="2.2" fill="{BG}"/>
  <circle cx="34.5" cy="31" r="2.2" fill="{BG}"/>
  <circle cx="42" cy="31" r="2.2" fill="{BG}"/>
  <text x="70" y="32" fill="{TEXT}" font-size="24" font-weight="700" font-family="{FONT}">SMS Hub</text>
  <text x="70" y="50" fill="{MUTED}" font-size="12.5" font-family="{FONT}">免费在线接码</text>'''))


# ============================================================================
# 02 · Hero 背景
# ============================================================================
def gen_hero():
    # hero-bg.svg — 抽象氛围背景（光轨 + 点阵），不含手机/气泡，
    # 因为页面右侧已渲染真实手机模型，背景再画一套会重叠打架。
    body = f'''  <defs>
    <radialGradient id="hbGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
      gradientTransform="translate(760 90) rotate(140) scale(620 380)">
      <stop stop-color="{PRIMARY}" stop-opacity=".34"/>
      <stop offset=".5" stop-color="{ACCENT}" stop-opacity=".13"/>
      <stop offset="1" stop-color="{BG}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="hbGlow2" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
      gradientTransform="translate(220 380) rotate(-30) scale(520 300)">
      <stop stop-color="{ACCENT}" stop-opacity=".16"/>
      <stop offset="1" stop-color="{BG}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="hbRail1" x1="0" y1="120" x2="1200" y2="300" gradientUnits="userSpaceOnUse">
      <stop stop-color="{PRIMARY}" stop-opacity="0"/>
      <stop offset=".28" stop-color="{PRIMARY_HOVER}" stop-opacity=".6"/>
      <stop offset=".66" stop-color="{ACCENT}" stop-opacity=".5"/>
      <stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="hbRail2" x1="0" y1="320" x2="1200" y2="90" gradientUnits="userSpaceOnUse">
      <stop stop-color="{ACCENT}" stop-opacity="0"/>
      <stop offset=".42" stop-color="{ACCENT}" stop-opacity=".38"/>
      <stop offset="1" stop-color="{PRIMARY}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="hbRail3" x1="0" y1="0" x2="1200" y2="0" gradientUnits="userSpaceOnUse">
      <stop stop-color="{PRIMARY}" stop-opacity="0"/>
      <stop offset=".5" stop-color="{PRIMARY}" stop-opacity=".3"/>
      <stop offset="1" stop-color="{PRIMARY}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="420" fill="{BG}"/>
  <rect width="1200" height="420" fill="url(#hbGlow)"/>
  <rect width="1200" height="420" fill="url(#hbGlow2)"/>

  <!-- 蓝绿轻量光轨（§44） -->
  <path d="M-40 300C180 220 300 120 520 96C740 72 900 150 1240 60" stroke="url(#hbRail1)" stroke-width="1.6"/>
  <path d="M-40 250C200 300 360 250 560 200C780 145 940 90 1240 130" stroke="url(#hbRail2)" stroke-width="1.2"/>
  <path d="M-40 350C220 310 420 340 640 290C860 240 1000 270 1240 210" stroke="url(#hbRail2)" stroke-width="1" stroke-opacity=".8"/>
  <path d="M-40 180C240 160 460 200 700 156C900 120 1060 140 1240 110" stroke="url(#hbRail3)" stroke-width="1"/>

  <!-- 点阵（左下 + 右上两块，中间留空给文案与手机） -->
  <g fill="{PRIMARY}" fill-opacity=".34">
    <circle cx="96" cy="330" r="1.6"/><circle cx="132" cy="352" r="1.6"/><circle cx="86" cy="372" r="1.6"/>
    <circle cx="150" cy="326" r="1.6"/><circle cx="168" cy="368" r="1.6"/><circle cx="112" cy="392" r="1.6"/>
    <circle cx="196" cy="344" r="1.6"/><circle cx="206" cy="386" r="1.6"/><circle cx="132" cy="404" r="1.6"/>
    <circle cx="1030" cy="60" r="1.6"/><circle cx="1064" cy="82" r="1.6"/><circle cx="1020" cy="102" r="1.6"/>
    <circle cx="1084" cy="56" r="1.6"/><circle cx="1102" cy="98" r="1.6"/><circle cx="1046" cy="122" r="1.6"/>
    <circle cx="1128" cy="74" r="1.6"/><circle cx="1140" cy="116" r="1.6"/><circle cx="1066" cy="134" r="1.6"/>
  </g>
  <g fill="{ACCENT}" fill-opacity=".3">
    <circle cx="60" cy="240" r="1.4"/><circle cx="100" cy="216" r="1.4"/><circle cx="142" cy="244" r="1.4"/>
    <circle cx="1160" cy="330" r="1.4"/><circle cx="1120" cy="356" r="1.4"/><circle cx="1152" cy="382" r="1.4"/>
  </g>
  <!-- 光点 -->
  <circle cx="700" cy="120" r="3.4" fill="{ACCENT}" fill-opacity=".9"/>
  <circle cx="980" cy="150" r="3" fill="{ACCENT}" fill-opacity=".7"/>
  <circle cx="420" cy="232" r="2.6" fill="{PRIMARY}" fill-opacity=".8"/>'''
    write("backgrounds/hero-bg.svg", svg(1200, 420, body))

    # 02b · 营销用完整版（含手机+气泡，用于分享图 / OG image）
    body_full = f'''  <defs>
    <radialGradient id="hmGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
      gradientTransform="translate(800 120) rotate(140) scale(560 340)">
      <stop stop-color="{PRIMARY}" stop-opacity=".32"/>
      <stop offset=".55" stop-color="{ACCENT}" stop-opacity=".11"/>
      <stop offset="1" stop-color="{BG}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="hmRail" x1="120" y1="60" x2="900" y2="300" gradientUnits="userSpaceOnUse">
      <stop stop-color="{PRIMARY}" stop-opacity="0"/>
      <stop offset=".35" stop-color="{PRIMARY_HOVER}" stop-opacity=".6"/>
      <stop offset=".7" stop-color="{ACCENT}" stop-opacity=".5"/>
      <stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="hmScreen" x1="820" y1="70" x2="1020" y2="330" gradientUnits="userSpaceOnUse">
      <stop stop-color="{SURFACE2}"/><stop offset="1" stop-color="#0A1120"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="420" fill="{BG}"/>
  <rect width="1200" height="420" fill="url(#hmGlow)"/>
  <path d="M-40 300C180 220 300 120 520 96C740 72 900 150 1240 60" stroke="url(#hmRail)" stroke-width="1.6"/>
  <path d="M-40 250C200 300 360 250 560 200C780 145 940 90 1240 130" stroke="url(#hmRail)" stroke-width="1.2"/>

  <!-- 手机 -->
  <g transform="translate(820 20)">
    <rect width="230" height="380" rx="34" fill="{BG}"/>
    <rect x="3" y="3" width="224" height="374" rx="31" fill="url(#hmScreen)"/>
    <rect x="88" y="14" width="54" height="10" rx="5" fill="#0A1120"/>
    <rect x="22" y="52" width="112" height="34" rx="10" fill="{SURFACE2}"/>
    <rect x="32" y="63" width="58" height="5" rx="2.5" fill="{MUTED}" fill-opacity=".6"/>
    <rect x="32" y="73" width="82" height="5" rx="2.5" fill="{MUTED}" fill-opacity=".35"/>
    <rect x="96" y="112" width="112" height="34" rx="10" fill="{SURFACE2}"/>
    <rect x="106" y="123" width="58" height="5" rx="2.5" fill="{MUTED}" fill-opacity=".6"/>
    <rect x="106" y="133" width="82" height="5" rx="2.5" fill="{MUTED}" fill-opacity=".35"/>
  </g>

  <!-- 短信气泡 -->
  <g transform="translate(470 118)">
    <rect width="252" height="86" rx="18" fill="{SURFACE}" stroke="{BORDER}"/>
    <rect x="16" y="20" width="34" height="34" rx="10" fill="{ACCENT}" fill-opacity=".18"/>
    <path d="M25 30H41C43.2 30 45 31.8 45 34V41C45 43.2 43.2 45 41 45H37L33 49V45H25C22.8 45 21 43.2 21 41V34C21 31.8 22.8 30 25 30Z" fill="{ACCENT}"/>
    <rect x="62" y="24" width="96" height="7" rx="3.5" fill="{TEXT}" fill-opacity=".9"/>
    <rect x="62" y="41" width="150" height="6" rx="3" fill="{MUTED}" fill-opacity=".55"/>
    <rect x="62" y="56" width="118" height="6" rx="3" fill="{MUTED}" fill-opacity=".35"/>
  </g>

  <!-- OTP 卡 -->
  <g transform="translate(694 160)">
    <rect width="128" height="76" rx="16" fill="{SURFACE}" stroke="{BORDER}"/>
    <text x="14" y="26" fill="{MUTED}" font-size="10.5" font-family="{FONT}">Your verification code is</text>
    <text x="14" y="60" fill="{ACCENT}" font-size="30" font-weight="800" letter-spacing="1.4" font-family="{FONT}">682491</text>
  </g>

  <!-- 悬浮 App 图标 -->
  <rect x="330" y="262" width="40" height="40" rx="12" fill="{SURFACE}" stroke="{BORDER}"/>
  <path d="M350 272a9 9 0 0 0-8.6 11.6l-1.4 4.4 4.5-1.4A9 9 0 1 0 350 272Z" fill="{PRIMARY}"/>
  <circle cx="350" cy="282" r="3.4" fill="{BG}"/>
  <rect x="382" y="300" width="40" height="40" rx="12" fill="{SURFACE}" stroke="{BORDER}"/>
  <path d="M402 310l11 5.5-11 5.5-11-5.5 11-5.5Zm0 13.5 7.5-3.7v5.7l-7.5 3.6-7.5-3.6v-5.7l7.5 3.7Z" fill="{ACCENT}"/>
  <rect x="440" y="330" width="40" height="40" rx="12" fill="{SURFACE}" stroke="{BORDER}"/>
  <path d="M460 340a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 3.4a5.6 5.6 0 1 1 0 11.2 5.6 5.6 0 0 1 0-11.2Zm5.4-4.6 3 3-2.6 2.6-3-3 2.6-2.6Z" fill="{SUCCESS}"/>'''
    write("backgrounds/hero-visual.svg", svg(1200, 420, body_full))

    # bg-gradient-1 — 蓝色径向
    write("backgrounds/bg-gradient-1.svg", svg(1200, 420, f'''  <defs>
    <radialGradient id="bg1a" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
      gradientTransform="translate(880 60) rotate(150) scale(700 420)">
      <stop stop-color="{PRIMARY}" stop-opacity=".38"/>
      <stop offset=".5" stop-color="{PRIMARY}" stop-opacity=".12"/>
      <stop offset="1" stop-color="{BG}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="bg1b" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
      gradientTransform="translate(160 400) rotate(-30) scale(520 300)">
      <stop stop-color="#1E3A8A" stop-opacity=".34"/>
      <stop offset="1" stop-color="{BG}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1200" height="420" fill="{BG}"/>
  <rect width="1200" height="420" fill="url(#bg1a)"/>
  <rect width="1200" height="420" fill="url(#bg1b)"/>'''))

    # bg-gradient-2 — 青色径向
    write("backgrounds/bg-gradient-2.svg", svg(1200, 420, f'''  <defs>
    <radialGradient id="bg2a" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
      gradientTransform="translate(320 340) rotate(-25) scale(760 440)">
      <stop stop-color="{ACCENT}" stop-opacity=".26"/>
      <stop offset=".5" stop-color="#0D9488" stop-opacity=".12"/>
      <stop offset="1" stop-color="{BG}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="bg2b" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
      gradientTransform="translate(1000 60) rotate(155) scale(560 320)">
      <stop stop-color="{PRIMARY}" stop-opacity=".22"/>
      <stop offset="1" stop-color="{BG}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1200" height="420" fill="{BG}"/>
  <rect width="1200" height="420" fill="url(#bg2a)"/>
  <rect width="1200" height="420" fill="url(#bg2b)"/>'''))

    # bg-wave — 波纹
    write("backgrounds/bg-wave.svg", svg(1200, 420, f'''  <defs>
    <linearGradient id="wvA" x1="0" y1="0" x2="1200" y2="0" gradientUnits="userSpaceOnUse">
      <stop stop-color="{PRIMARY}" stop-opacity="0"/>
      <stop offset=".4" stop-color="{PRIMARY_HOVER}" stop-opacity=".55"/>
      <stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="wvB" x1="0" y1="0" x2="1200" y2="0" gradientUnits="userSpaceOnUse">
      <stop stop-color="{ACCENT}" stop-opacity="0"/>
      <stop offset=".45" stop-color="{ACCENT}" stop-opacity=".45"/>
      <stop offset="1" stop-color="{PRIMARY}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="420" fill="{BG}"/>
  <path d="M-20 250C160 190 320 300 500 250C680 200 840 290 1020 230C1100 205 1160 220 1240 200" stroke="url(#wvA)" stroke-width="2"/>
  <path d="M-20 290C160 230 320 340 500 290C680 240 840 330 1020 270C1100 245 1160 260 1240 240" stroke="url(#wvB)" stroke-width="1.4"/>
  <path d="M-20 330C160 275 320 380 500 330C680 280 840 370 1020 315C1100 290 1160 305 1240 285" stroke="url(#wvB)" stroke-width="1" stroke-opacity=".7"/>
  <path d="M-20 210C160 155 320 262 500 212C680 162 840 252 1020 195C1100 170 1160 185 1240 165" stroke="url(#wvA)" stroke-width="1" stroke-opacity=".6"/>'''))

    # 更新 world-map-bg 到新 token（保留点阵手感，换配色）
    random.seed(42)
    dots = []
    clusters = [(240, 110), (520, 130), (650, 120), (700, 160), (820, 185), (900, 140), (420, 200), (300, 230)]
    for cx, cy in clusters:
        for _ in range(22):
            dx = int(random.gauss(0, 26))
            dy = int(random.gauss(0, 30))
            dots.append(f'<circle cx="{cx+dx}" cy="{cy+dy}" r="1.7" fill="{PRIMARY}" fill-opacity=".5"/>')
    write("backgrounds/world-map-bg.svg", svg(1200, 420, f'''  <defs>
    <radialGradient id="wmGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
      gradientTransform="translate(720 140) rotate(145) scale(500 300)">
      <stop stop-color="{PRIMARY}" stop-opacity=".22"/>
      <stop offset="1" stop-color="{BG}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="wmLine" x1="220" y1="80" x2="900" y2="280" gradientUnits="userSpaceOnUse">
      <stop stop-color="{PRIMARY}" stop-opacity=".12"/>
      <stop offset=".5" stop-color="{ACCENT}" stop-opacity=".6"/>
      <stop offset="1" stop-color="{PRIMARY}" stop-opacity=".08"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="420" fill="{BG}"/>
  <rect width="1200" height="420" fill="url(#wmGlow)"/>
  <g>
    {chr(10).join("    " + d for d in dots)}
  </g>
  <path d="M282 146C400 76 540 68 680 118C780 155 840 195 930 145" stroke="url(#wmLine)" stroke-width="1.4"/>
  <path d="M500 205C620 122 770 125 880 215" stroke="url(#wmLine)" stroke-width="1.2"/>
  <circle cx="680" cy="118" r="4" fill="{ACCENT}"/>
  <circle cx="930" cy="145" r="4" fill="{ACCENT}"/>
  <circle cx="880" cy="215" r="4" fill="{ACCENT}"/>'''))

    # grid-overlay 保持极淡，对齐新底色
    write("backgrounds/grid-overlay.svg", svg(160, 160, f'''  <path d="M40 0V160M80 0V160M120 0V160M0 40H160M0 80H160M0 120H160" stroke="#FFFFFF" stroke-opacity=".035" stroke-width="1"/>'''))


# ============================================================================
# 05 · 品牌元素图（PNG 风格图标，此处统一输出 SVG）
# ============================================================================
def gen_elements():
    # element-sms-bubble — 立体短信气泡
    write("elements/element-sms-bubble.svg", svg(140, 140, f'''  <defs>
    <linearGradient id="bsq" x1="20" y1="18" x2="120" y2="122" gradientUnits="userSpaceOnUse">
      <stop stop-color="{PRIMARY_HOVER}"/><stop offset="1" stop-color="{PRIMARY}"/>
    </linearGradient>
    <filter id="bShadow" x="-30%" y="-30%" width="160%" height="170%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000000" flood-opacity=".45"/>
    </filter>
  </defs>
  <g filter="url(#bShadow)">
    <rect x="20" y="22" width="100" height="78" rx="22" fill="url(#bsq)"/>
    <path d="M48 100L44 122L70 100Z" fill="{PRIMARY}"/>
    <rect x="22" y="24" width="96" height="30" rx="15" fill="#FFFFFF" fill-opacity=".14"/>
  </g>
  <text x="70" y="72" fill="#FFFFFF" font-size="27" font-weight="800" text-anchor="middle" letter-spacing="1" font-family="{FONT}">SMS</text>'''))

    # element-otp-card — OTP 卡片
    write("elements/element-otp-card.svg", svg(160, 120, f'''  <defs>
    <linearGradient id="otpFill" x1="14" y1="14" x2="146" y2="106" gradientUnits="userSpaceOnUse">
      <stop stop-color="{SURFACE2}"/><stop offset="1" stop-color="{SURFACE}"/>
    </linearGradient>
    <filter id="otpShadow" x="-25%" y="-25%" width="150%" height="165%">
      <feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#000000" flood-opacity=".5"/>
    </filter>
    <linearGradient id="otpEdge" x1="14" y1="14" x2="146" y2="106" gradientUnits="userSpaceOnUse">
      <stop stop-color="{PRIMARY}" stop-opacity=".6"/><stop offset="1" stop-color="{ACCENT}" stop-opacity=".45"/>
    </linearGradient>
  </defs>
  <g filter="url(#otpShadow)">
    <rect x="14" y="14" width="132" height="92" rx="18" fill="url(#otpFill)" stroke="url(#otpEdge)"/>
    <rect x="14" y="14" width="132" height="92" rx="18" fill="none" stroke="{BORDER}"/>
  </g>
  <text x="30" y="46" fill="{TEXT}" font-size="11" font-family="{FONT}">Your verification code is</text>
  <text x="30" y="82" fill="{ACCENT}" font-size="32" font-weight="800" letter-spacing="1.6" font-family="{FONT}">682491</text>'''))

    # element-shield — 盾牌
    write("elements/element-shield.svg", svg(140, 140, f'''  <defs>
    <linearGradient id="shFill" x1="26" y1="16" x2="114" y2="126" gradientUnits="userSpaceOnUse">
      <stop stop-color="{ACCENT}"/><stop offset="1" stop-color="#0E8F76"/>
    </linearGradient>
    <filter id="shShadow" x="-30%" y="-25%" width="160%" height="165%">
      <feDropShadow dx="0" dy="9" stdDeviation="11" flood-color="#000000" flood-opacity=".48"/>
    </filter>
  </defs>
  <g filter="url(#shShadow)">
    <path d="M70 14L114 32V66C114 96 94 118 70 126C46 118 26 96 26 66V32L70 14Z" fill="url(#shFill)"/>
    <path d="M70 20L108 36V66C108 91 91 110 70 118C49 110 32 91 32 66V36L70 20Z" fill="#FFFFFF" fill-opacity=".10"/>
  </g>
  <path d="M52 68L64 81L89 52" stroke="#FFFFFF" stroke-width="8.5" stroke-linecap="round" stroke-linejoin="round"/>'''))

    # element-paper-plane — 纸飞机
    write("elements/element-paper-plane.svg", svg(150, 140, f'''  <defs>
    <linearGradient id="ppA" x1="18" y1="62" x2="134" y2="34" gradientUnits="userSpaceOnUse">
      <stop stop-color="{PRIMARY}"/><stop offset="1" stop-color="{PRIMARY_HOVER}"/>
    </linearGradient>
    <linearGradient id="ppB" x1="18" y1="76" x2="134" y2="102" gradientUnits="userSpaceOnUse">
      <stop stop-color="#7FA8FF"/><stop offset="1" stop-color="{PRIMARY}"/>
    </linearGradient>
    <filter id="ppShadow" x="-25%" y="-30%" width="155%" height="170%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000000" flood-opacity=".45"/>
    </filter>
  </defs>
  <g filter="url(#ppShadow)">
    <path d="M18 68L134 26L92 122L68 84L18 68Z" fill="url(#ppA)"/>
    <path d="M18 68L134 26L68 84L18 68Z" fill="#FFFFFF" fill-opacity=".16"/>
    <path d="M68 84L92 122L134 26L68 84Z" fill="url(#ppB)"/>
    <path d="M68 84L134 26" stroke="#FFFFFF" stroke-opacity=".28" stroke-width="1.5"/>
  </g>'''))

    # phone-mockup — 手机模型（独立可复用）
    write("elements/phone-mockup.svg", svg(260, 440, f'''  <defs>
    <linearGradient id="pmFrame" x1="0" y1="0" x2="260" y2="440" gradientUnits="userSpaceOnUse">
      <stop stop-color="#2A3646"/><stop offset=".5" stop-color="#141C28"/><stop offset="1" stop-color="#2A3646"/>
    </linearGradient>
    <linearGradient id="pmScr" x1="20" y1="20" x2="240" y2="420" gradientUnits="userSpaceOnUse">
      <stop stop-color="#16202E"/><stop offset="1" stop-color="#0A1120"/>
    </linearGradient>
    <filter id="pmShadow" x="-20%" y="-10%" width="140%" height="125%">
      <feDropShadow dx="0" dy="18" stdDeviation="22" flood-color="#000000" flood-opacity=".6"/>
    </filter>
  </defs>
  <g filter="url(#pmShadow)">
    <rect width="260" height="440" rx="40" fill="url(#pmFrame)"/>
    <rect x="5" y="5" width="250" height="430" rx="36" fill="{BG}"/>
    <rect x="11" y="11" width="238" height="418" rx="31" fill="url(#pmScr)"/>
  </g>
  <rect x="98" y="20" width="64" height="11" rx="5.5" fill="#0A1120"/>
  <!-- 短信内容 -->
  <rect x="30" y="62" width="120" height="38" rx="12" fill="{SURFACE2}"/>
  <rect x="42" y="74" width="64" height="5.5" rx="2.75" fill="{MUTED}" fill-opacity=".6"/>
  <rect x="42" y="85" width="90" height="5.5" rx="2.75" fill="{MUTED}" fill-opacity=".32"/>
  <rect x="110" y="126" width="120" height="38" rx="12" fill="{SURFACE2}"/>
  <rect x="122" y="138" width="64" height="5.5" rx="2.75" fill="{MUTED}" fill-opacity=".6"/>
  <rect x="122" y="149" width="90" height="5.5" rx="2.75" fill="{MUTED}" fill-opacity=".32"/>
  <rect x="30" y="190" width="120" height="38" rx="12" fill="{SURFACE2}"/>
  <rect x="42" y="202" width="64" height="5.5" rx="2.75" fill="{MUTED}" fill-opacity=".6"/>
  <rect x="42" y="213" width="90" height="5.5" rx="2.75" fill="{MUTED}" fill-opacity=".32"/>
  <!-- OTP 卡 -->
  <rect x="34" y="252" width="192" height="86" rx="16" fill="{SURFACE}" stroke="{BORDER}"/>
  <text x="50" y="282" fill="{MUTED}" font-size="11" font-family="{FONT}">Your verification code is</text>
  <text x="50" y="320" fill="{ACCENT}" font-size="34" font-weight="800" letter-spacing="1.8" font-family="{FONT}">682491</text>'''))


# ============================================================================
# 04 · 状态徽标（圆点式）
# ============================================================================
def _status_dot(name, color, label_cn):
    write(f"status/status-{name}.svg", svg(120, 36, f'''  <rect width="120" height="36" rx="18" fill="{SURFACE}" stroke="{BORDER}"/>
  <circle cx="22" cy="18" r="8" fill="{color}" fill-opacity=".18"/>
  <circle cx="22" cy="18" r="4" fill="{color}"/>
  <text x="40" y="23" fill="{color}" font-size="13" font-weight="600" font-family="{FONT}">{label_cn}</text>'''))


def gen_status():
    _status_dot("available", SUCCESS, "可用")
    _status_dot("low_usage", WARNING, "较少使用")
    _status_dot("unverified", MUTED_STATUS, "暂未验证")
    _status_dot("recommended", PRIMARY, "推荐")
    _status_dot("offline", "#EF4444", "不可用")

    # 纯圆点（表格内嵌用）
    for nm, color in (("available", SUCCESS), ("low_usage", WARNING), ("unverified", MUTED_STATUS)):
        write(f"status/dot-{nm}.svg", svg(20, 20, f'''  <circle cx="10" cy="10" r="5" fill="{color}"/>'''))


# ============================================================================
# 09 · 角标 Badge
# ============================================================================
def _badge(name, label, color, style="solid", icon=None):
    w = 24 + len(label) * 13
    w = max(w, 74)
    body = ""
    if style == "solid":
        body = f'''  <rect x="0" y="6" width="{w}" height="26" rx="13" fill="{color}"/>
  <text x="{w/2}" y="24" fill="#FFFFFF" font-size="13" font-weight="700" text-anchor="middle" font-family="{FONT}">{label}</text>'''
    else:
        body = f'''  <rect x="0" y="6" width="{w}" height="26" rx="13" fill="{color}" fill-opacity=".16" stroke="{color}" stroke-opacity=".45"/>
  <text x="{w/2}" y="24" fill="{color}" font-size="13" font-weight="700" text-anchor="middle" font-family="{FONT}">{label}</text>'''
    write(f"badges/badge-{name}.svg", svg(w, 38, body))


def gen_badges():
    _badge("new", "NEW", "#EF4444")
    _badge("hot", "HOT", WARNING)
    _badge("active", "活跃", WARNING, "soft")
    _badge("safe", "安全", SUCCESS, "soft")
    _badge("time", "5 分钟前", PRIMARY, "soft")
    _badge("sync", "刚刚同步", PRIMARY, "soft")
    _badge("success", "已复制", SUCCESS, "soft")
    _badge("waiting", "等待中", DIM, "soft")
    _badge("recommended", "推荐", PRIMARY, "solid")


# ============================================================================
# 08 · 信任元素 USP
# ============================================================================
def _usp(name, label, path_d):
    write(f"usp/usp-{name}.svg", svg(120, 120, f'''  <rect x="26" y="14" width="68" height="68" rx="20" fill="{PRIMARY}" fill-opacity=".10" stroke="{BORDER}"/>
  <g transform="translate(36 24)">
    <g fill="none" stroke="{PRIMARY}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
      {path_d}
    </g>
  </g>
  <text x="60" y="104" fill="{TEXT}" font-size="13" font-weight="600" text-anchor="middle" font-family="{FONT}">{label}</text>'''))


def gen_usp():
    _usp("fast", "快速", '<path d="M28 4L10 28H22L20 44L38 20H26L28 4Z" stroke="none" fill="#4F7FFF"/>')
    _usp("free", "免费", '<circle cx="24" cy="30" r="6.5"/><circle cx="6" cy="14" r="6.5"/><circle cx="42" cy="14" r="6.5"/><path d="M11 18l9 7M37 18l-9 7M18.5 30h11"/>')
    _usp("no-register", "无需注册", '<circle cx="24" cy="12" r="7"/><path d="M10 38c0-8 6.3-13 14-13s14 5 14 13"/><path d="M31 8l9 9M40 8l-9 9"/>')
    _usp("public", "在线查看", '<path d="M2 24s8-13 22-13 22 13 22 13-8 13-22 13S2 24 2 24Z"/><circle cx="24" cy="24" r="5.5"/><circle cx="24" cy="24" r="1.6" fill="#4F7FFF" stroke="none"/>')
    _usp("multi-country", "多国家", '<circle cx="24" cy="24" r="18"/><path d="M6 24h36M24 6c5 5 7.5 11.5 7.5 18S29 43 24 42 16.5 30.5 16.5 24 19 11 24 6Z"/>')
    _usp("safe", "安全", '<path d="M24 4l16 7v12c0 11-7 18.5-16 21-9-2.5-16-10-16-21V11l16-7Z"/><path d="M17 24l5.5 5.5L32 19"/>')
    _usp("stable", "稳定", '<path d="M6 36V22M16 36V12M26 36V26M36 36V16"/><rect x="3" y="36" width="38" height="2.5" rx="1.25"/>')
    _usp("easy", "简单易用", '<circle cx="24" cy="13" r="6.5"/><path d="M11 40c0-8 5.8-13 13-13s13 5 13 13"/><path d="M36 8l4 4 7-8"/>')


# ============================================================================
# 11 · 空态插画
# ============================================================================
def gen_empty():
    write("empty/empty-inbox.svg", svg(200, 160, f'''  <defs>
    <linearGradient id="eibA" x1="40" y1="50" x2="160" y2="130" gradientUnits="userSpaceOnUse">
      <stop stop-color="{PRIMARY_HOVER}"/><stop offset="1" stop-color="{PRIMARY}"/>
    </linearGradient>
  </defs>
  <!-- 抽屉盒 -->
  <rect x="46" y="72" width="108" height="60" rx="12" fill="{SURFACE2}" stroke="{BORDER}"/>
  <path d="M46 92h26l6 10h44l6-10h26" stroke="{BORDER}" stroke-width="1.6" fill="none"/>
  <!-- 弹出信件 -->
  <g>
    <rect x="66" y="34" width="68" height="48" rx="8" fill="url(#eibA)"/>
    <path d="M66 40l34 22 34-22" stroke="#FFFFFF" stroke-opacity=".7" stroke-width="2" fill="none"/>
  </g>
  <!-- 光晕 -->
  <ellipse cx="100" cy="142" rx="62" ry="9" fill="{PRIMARY}" fill-opacity=".12"/>
  <!-- 点缀 -->
  <circle cx="40" cy="52" r="2.5" fill="{ACCENT}" fill-opacity=".7"/>
  <circle cx="164" cy="66" r="2.5" fill="{ACCENT}" fill-opacity=".7"/>
  <circle cx="158" cy="34" r="1.8" fill="{PRIMARY}" fill-opacity=".7"/>'''))

    write("empty/waiting-sms.svg", svg(200, 160, f'''  <defs>
    <linearGradient id="wsA" x1="48" y1="30" x2="152" y2="128" gradientUnits="userSpaceOnUse">
      <stop stop-color="{ACCENT}"/><stop offset="1" stop-color="#0E8F76"/>
    </linearGradient>
  </defs>
  <!-- 信封+时钟 -->
  <g>
    <rect x="52" y="52" width="86" height="58" rx="10" fill="{SURFACE2}" stroke="{BORDER}"/>
    <path d="M52 60l43 28 43-28" stroke="{MUTED}" stroke-opacity=".7" stroke-width="2" fill="none"/>
  </g>
  <circle cx="146" cy="52" r="28" fill="{SURFACE}" stroke="url(#wsA)" stroke-width="2.4"/>
  <path d="M146 36v17l11 7" stroke="{ACCENT}" stroke-width="2.6" stroke-linecap="round" fill="none"/>
  <!-- 光晕与点缀 -->
  <ellipse cx="100" cy="140" rx="60" ry="8" fill="{ACCENT}" fill-opacity=".12"/>
  <circle cx="36" cy="44" r="2.5" fill="{PRIMARY}" fill-opacity=".7"/>
  <circle cx="176" cy="106" r="2" fill="{ACCENT}" fill-opacity=".7"/>
  <circle cx="30" cy="104" r="1.8" fill="{ACCENT}" fill-opacity=".6"/>'''))

    write("empty/empty-search.svg", svg(200, 160, f'''  <circle cx="88" cy="66" r="40" fill="{SURFACE2}" stroke="{BORDER}" stroke-width="2"/>
  <circle cx="88" cy="66" r="26" fill="none" stroke="{MUTED}" stroke-opacity=".45" stroke-width="2"/>
  <path d="M118 96l30 30" stroke="{PRIMARY}" stroke-width="7" stroke-linecap="round"/>
  <path d="M74 62h28M74 74h18" stroke="{MUTED}" stroke-opacity=".55" stroke-width="3" stroke-linecap="round"/>
  <circle cx="42" cy="34" r="2.5" fill="{ACCENT}" fill-opacity=".7"/>
  <circle cx="164" cy="132" r="2" fill="{PRIMARY}" fill-opacity=".7"/>'''))

    write("empty/empty-error.svg", svg(200, 160, f'''  <circle cx="100" cy="74" r="42" fill="{WARNING}" fill-opacity=".10" stroke="{WARNING}" stroke-opacity=".45" stroke-width="2"/>
  <path d="M100 50v30" stroke="{WARNING}" stroke-width="6" stroke-linecap="round"/>
  <circle cx="100" cy="96" r="3.6" fill="{WARNING}"/>
  <ellipse cx="100" cy="138" rx="58" ry="8" fill="{WARNING}" fill-opacity=".10"/>
  <circle cx="44" cy="40" r="2.5" fill="{WARNING}" fill-opacity=".6"/>
  <circle cx="160" cy="120" r="2" fill="{WARNING}" fill-opacity=".6"/>'''))


# ============================================================================
# 12 · 通用图标（重写为统一 stroke 风格，外加扩展）
# ============================================================================
def _icon_stroke(body, w=24, h=24, extra_defs=""):
    return svg(w, h, f'''{extra_defs}  <g fill="none" stroke="{MUTED}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
{body}
  </g>'''.replace("__ACCENT__", ACCENT).replace("__MUTED__", MUTED).replace("__PRIMARY__", PRIMARY))


ICONS = {
    # 已有：统一风格化
    "search": '<circle cx="10.5" cy="10.5" r="6.2"/><path d="M15.2 15.2L20 20"/>',
    "filter": '<path d="M3.5 5.5h17M6.5 12h11M9.5 18.5h5"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20 3.6V8.4h-4.8"/>',
    "copy": '<rect x="9" y="9" width="11.5" height="11.5" rx="2.5"/><path d="M15 9V6.5A2.5 2.5 0 0 0 12.5 4h-6A2.5 2.5 0 0 0 4 6.5v6A2.5 2.5 0 0 0 6.5 15H9"/>',
    "external-link": '<path d="M14 4h6v6M20 4l-8.5 8.5"/><path d="M18 14v4.5A1.5 1.5 0 0 1 16.5 20h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
    "message": '<path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v8a2.5 2.5 0 0 1-2.5 2.5H11l-4 4v-4H6.5A2.5 2.5 0 0 1 4 14.5v-8Z"/>',
    "inbox": '<path d="M4 13.5l2.6-7A2 2 0 0 1 8.5 5h7a2 2 0 0 1 1.9 1.5l2.6 7v4A2 2 0 0 1 18 19.5H6a2 2 0 0 1-2-2v-4Z"/><path d="M4 13.5h4l1.4 2.5h5.2L16 13.5h4"/>',
    "phone": '<rect x="7" y="3" width="10" height="18" rx="2.6"/><path d="M10.5 6h3"/><circle cx="12" cy="18" r=".9" fill="__MUTED__"/>',
    "globe": '<circle cx="12" cy="12" r="8.4"/><path d="M3.6 12h16.8M12 3.6c2.4 2.4 3.6 5.3 3.6 8.4S14.4 18 12 20.4 8.4 15.1 8.4 12 9.6 6 12 3.6Z"/>',
    "home": '<path d="M4 10.6 12 4l8 6.6V19a1.6 1.6 0 0 1-1.6 1.6h-3.9v-6.2H9.5v6.2H5.6A1.6 1.6 0 0 1 4 19v-8.4Z"/>',
    "star": '<path d="M12 3.6l2.6 5.3 5.9.85-4.25 4.15 1 5.85L12 16.95l-5.25 2.8 1-5.85L3.5 9.75l5.9-.85L12 3.6Z"/>',
    "swap": '<path d="M6.5 4.5L4 7l2.5 2.5M4 7h13a2.5 2.5 0 0 1 0 5h-1M17.5 19.5L20 17l-2.5-2.5M20 17H7a2.5 2.5 0 0 1 0-5h1"/>',
    "bell": '<path d="M17 10a5 5 0 1 0-10 0c0 5-2 6-2 6h14s-2-1-2-6Z"/><path d="M10.3 19.5a2 2 0 0 0 3.4 0"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .32 1.77l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.6 1.6 0 0 0 15 19.4a1.6 1.6 0 0 0-1 1.47V21a2 2 0 0 1-4 0v-.1A1.6 1.6 0 0 0 9 19.4a1.6 1.6 0 0 0-1.77.32l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.6 1.6 0 0 0 4.6 15a1.6 1.6 0 0 0-1.47-1H3a2 2 0 0 1 0-4h.1A1.6 1.6 0 0 0 4.6 9a1.6 1.6 0 0 0-.32-1.77l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.6 1.6 0 0 0 9 4.6h.1A1.6 1.6 0 0 0 10 3.13V3a2 2 0 0 1 4 0v.1A1.6 1.6 0 0 0 15 4.6a1.6 1.6 0 0 0 1.77-.32l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.6 1.6 0 0 0 19.4 9v.1a1.6 1.6 0 0 0 1.47 1H21a2 2 0 0 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1Z"/>',
    "help": '<circle cx="12" cy="12" r="8.4"/><path d="M9.6 9.4a2.5 2.5 0 0 1 4.9.6c0 1.7-2.5 2.5-2.5 2.5"/><circle cx="12" cy="16.6" r=".9" fill="__MUTED__"/>',
    "guide": '<path d="M4 5.4A1.4 1.4 0 0 1 5.4 4h4.1A2.5 2.5 0 0 1 12 6.5v13a2.2 2.2 0 0 0-2.2-2.2H4V5.4Z"/><path d="M20 5.4A1.4 1.4 0 0 0 18.6 4h-4.1A2.5 2.5 0 0 0 12 6.5v13a2.2 2.2 0 0 1 2.2-2.2H20V5.4Z"/>',
    "shield": '<path d="M12 3l7 3v5.5c0 5-3.1 8.4-7 9.5-3.9-1.1-7-4.5-7-9.5V6l7-3Z"/><path d="M8.8 11.6l2.4 2.4 4-4.4"/>',
    "country": '<path d="M12 21.4s6.6-5.4 6.6-11a6.6 6.6 0 1 0-13.2 0c0 5.6 6.6 11 6.6 11Z"/><circle cx="12" cy="10.2" r="2.4"/>',
    "database": '<ellipse cx="12" cy="6" rx="7.4" ry="3"/><path d="M4.6 6v12c0 1.66 3.31 3 7.4 3s7.4-1.34 7.4-3V6"/><path d="M4.6 12c0 1.66 3.31 3 7.4 3s7.4-1.34 7.4-3"/>',
    "sms": '<path d="M4 5.5C4 4.7 4.7 4 5.5 4H18.5C19.3 4 20 4.7 20 5.5V14.5C20 15.3 19.3 16 18.5 16H11L7 20V16H5.5C4.7 16 4 15.3 4 14.5V5.5Z"/><circle cx="9" cy="10" r="1" fill="__ACCENT__" stroke="none"/><circle cx="12" cy="10" r="1" fill="__ACCENT__" stroke="none"/><circle cx="15" cy="10" r="1" fill="__ACCENT__" stroke="none"/>',
    "warning": '<path d="M12 4.5 21 19.5H3L12 4.5Z"/><path d="M12 10v4"/><circle cx="12" cy="16.7" r=".9" fill="__MUTED__" stroke="none"/>',
    "clock": '<circle cx="12" cy="12" r="8.4"/><path d="M12 7.4V12l3.2 2"/>',
    "layers": '<path d="M12 3.6 21 8l-9 4.4L3 8l9-4.4Z"/><path d="M3 12l9 4.4 9-4.4"/><path d="M3 16l9 4.4 9-4.4"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "chevron-right": '<path d="M9.5 5.5 16 12l-6.5 6.5"/>',
    "chevron-down": '<path d="M5.5 9.5 12 16l6.5-6.5"/>',
    "chevron-left": '<path d="M14.5 5.5 8 12l6.5 6.5"/>',
    "arrow-right": '<path d="M4 12h15M13.5 6.5 20 12l-6.5 5.5"/>',
    "info": '<circle cx="12" cy="12" r="8.4"/><path d="M12 11v5.4"/><circle cx="12" cy="8.1" r=".9" fill="__MUTED__" stroke="none"/>',
    "check": '<path d="M5 12.5 10 17.5 19.5 6.5"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "mail": '<rect x="3.5" y="5.5" width="17" height="13" rx="2.5"/><path d="M4 7l8 5.6L20 7"/>',
    "download": '<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5"/><path d="M4.5 19.5h15"/>',
    "eye": '<path d="M2.5 12S6.5 5.5 12 5.5 21.5 12 21.5 12 17.5 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
    "user": '<circle cx="12" cy="8.2" r="3.8"/><path d="M4.8 20c0-4 3.2-6.6 7.2-6.6S19.2 16 19.2 20"/>',
    "lock": '<rect x="4.8" y="10.5" width="14.4" height="9.5" rx="2.4"/><path d="M8.4 10.5V7.8a3.6 3.6 0 0 1 7.2 0v2.7"/>',
    "sparkles": '<path d="M12 3.5l1.8 4.3 4.3 1.8-4.3 1.8L12 15.7l-1.8-4.3L5.9 9.6l4.3-1.8L12 3.5Z"/><path d="M18.6 15.2l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8.8-1.9Z"/>',
    "zap": '<path d="M13.5 3 5.5 13.4h5.4L10.5 21l8-10.4h-5.4L13.5 3Z"/>',
    "sort": '<path d="M7 4v16M7 4 3.5 8M7 4l3.5 4"/><path d="M17 20V4M17 20l-3.5-4M17 20l3.5-4"/>',
    "calendar": '<rect x="3.8" y="5.5" width="16.4" height="14" rx="2.4"/><path d="M3.8 10h16.4M8.5 3.6v3.6M15.5 3.6v3.6"/>',
    "activity": '<path d="M3 12h4l2.5-6 4 13L16 12h5"/>',
    "share": '<circle cx="6" cy="12" r="2.6"/><circle cx="18" cy="6.4" r="2.6"/><circle cx="18" cy="17.6" r="2.6"/><path d="M8.3 10.8 15.7 7.6M8.3 13.2l7.4 3.2"/>',
    "logout": '<path d="M10 20H6.5A2.5 2.5 0 0 1 4 17.5v-11A2.5 2.5 0 0 1 6.5 4H10"/><path d="M15.5 8 19.5 12l-4 4M19.5 12H9.5"/>',
    "empty-box": '<path d="M4 13.5l2.6-7A2 2 0 0 1 8.5 5h7a2 2 0 0 1 1.9 1.5l2.6 7v4A2 2 0 0 1 18 19.5H6a2 2 0 0 1-2-2v-4Z"/><path d="M4 13.5h4l1.4 2.5h5.2L16 13.5h4"/>',
}


def gen_icons():
    for name, body in ICONS.items():
        write(f"icons/{name}.svg", _icon_stroke("    " + body.replace("><", ">\n    <")))

    # 旧的 status-* 图标保留但重画为规范圆点
    _status_dot_map = {
        "status-online": (SUCCESS, "在线"),
        "status-recent": (WARNING, "最近"),
        "status-unknown": (MUTED_STATUS, "未知"),
    }
    for nm, (color, label) in _status_dot_map.items():
        write(f"icons/{nm}.svg", svg(24, 24, f'''  <circle cx="12" cy="12" r="4.4" fill="{color}"/>
  <circle cx="12" cy="12" r="8" fill="{color}" fill-opacity=".18"/>'''))


# ============================================================================
# 10 · 服务图标（自定义识别图形，非商标复刻）
# ============================================================================
def gen_services():
    services = {
        "google": ("#4285F4", '<circular-center/>'),
        "telegram": ("#29A9EB", '<paper/>'),
        "whatsapp": ("#25D366", '<phone-bubble/>'),
        "facebook": ("#1877F2", '<f/>'),
        "twitter": ("#0F1419", '<bird/>'),
        "instagram": ("#E1306C", '<cam/>'),
    }
    inner = {
        # G 由四段弧 + 横杠构成，几何自洽
        "google": '<path d="M24 16.6c1.96 0 3.72.68 5.11 2l3.8-3.8A11.4 11.4 0 0 0 24 11.4c-4.5 0-8.38 2.58-10.24 6.34l4.42 3.43A6.79 6.79 0 0 1 24 16.6Z" fill="#EA4335"/>'
                  '<path d="M35.28 24.3c0-.79-.07-1.55-.2-2.3H24v4.35h6.32a5.4 5.4 0 0 1-2.35 3.55l3.87 3a11.4 11.4 0 0 0 3.44-8.6Z" fill="#4285F4"/>'
                  '<path d="M13.76 26.24a6.8 6.8 0 0 1-.36-2.24c0-.78.13-1.53.36-2.24l-4.42-3.43A11.4 11.4 0 0 0 12.6 30.6l3.9-3.02a6.79 6.79 0 0 1-2.74-1.34Z" fill="#FBBC05"/>'
                  '<path d="M24 36.6c3.08 0 5.66-1.02 7.55-2.77l-3.87-3a6.8 6.8 0 0 1-10.1-3.57l-4.42 3.42A11.4 11.4 0 0 0 24 36.6Z" fill="#34A853"/>',
        "telegram": '<path d="M34.6 14.6L11.4 23.6c-1.1.43-1.09 1.06-.19 1.33l4.35 1.36 1.6 4.9c.2.55.35.75.71.75.35 0 .5-.15.7-.35l1.75-1.7 4.05 2.99c.75.41 1.28.2 1.47-.69l2.65-12.5c.27-1.09-.41-1.58-1.12-1.27Zm-3.1 3.1l-8.05 7.35c-.35.32-.5.55-.56.85l-.32 2.3-1-3.5 10.5-7.4c.35-.24.66-.11.43.4Z" fill="#FFFFFF"/>',
        "whatsapp": '<path d="M24 12.4A11.5 11.5 0 0 0 14.1 29.7L12.6 35l5.45-1.43A11.5 11.5 0 1 0 24 12.4Zm0 21a9.5 9.5 0 0 1-4.85-1.33l-.35-.21-3.2.84.86-3.13-.23-.36A9.5 9.5 0 1 1 24 33.4Z" fill="#FFFFFF"/>'
                    '<path d="M20.1 18.2c-.22-.5-.45-.5-.62-.5h-.53c-.18 0-.48.07-.73.35-.25.28-.96.94-.96 2.28 0 1.35.98 2.65 1.12 2.83.14.18 1.9 2.9 4.6 4.06 2.25.97 2.7.78 3.19.73.49-.05 1.58-.64 1.8-1.26.22-.62.22-1.15.15-1.26-.07-.11-.25-.18-.53-.32-.28-.14-1.58-.78-1.83-.87-.25-.09-.43-.14-.6.14-.18.28-.7.87-.86 1.05-.16.18-.31.2-.6.07-.28-.14-1.2-.44-2.28-1.4-.84-.75-1.4-1.68-1.57-1.96-.16-.28-.02-.43.12-.57.13-.13.28-.32.42-.49.14-.16.19-.28.28-.46.09-.18.05-.34-.02-.48-.07-.14-.63-1.44-.86-1.97Z" fill="#FFFFFF"/>',
        "facebook": '<path d="M27.9 17.4h-2.2c-.87 0-1.44.5-1.44 1.55V21h3.76l-.58 3.16h-3.18V35h-4.04v-10.84h-2.5V21h2.5v-2.18c0-2.6 1.55-4.62 4.42-4.62h3.26v3.2Z" fill="#FFFFFF"/>',
        "twitter": '<path d="M35 15.6c-.85-.38-1.76-.63-2.72-.75a4.9 4.9 0 0 1 2.05 2.7c-.94-.55-1.97-.94-3.07-1.16a4.7 4.7 0 0 0-8.06 3.25c0 .37.04.72.12 1.06-3.93-.2-7.4-2.08-9.72-4.94a4.7 4.7 0 0 0 1.44 6.25 4.6 4.6 0 0 1-2.1-.6v.06a4.74 4.74 0 0 0 3.76 4.62c-.4.11-.82.17-1.25.17-.31 0-.61-.03-.9-.09a4.7 4.7 0 0 0 4.38 3.27 9.43 9.43 0 0 1-6.93 1.92 13.3 13.3 0 0 0 7.2 2.1c8.65 0 13.38-7.16 13.38-13.37 0-.2 0-.4-.01-.6a9.5 9.5 0 0 0 2.43-2.54Z" fill="#FFFFFF"/>',
        "instagram": '<rect x="14.5" y="14.5" width="19" height="19" rx="5.6" stroke="#FFFFFF" stroke-width="2.4" fill="none"/>'
                     '<circle cx="24" cy="24" r="4.6" stroke="#FFFFFF" stroke-width="2.4" fill="none"/>'
                     '<circle cx="29.6" cy="18.4" r="1.35" fill="#FFFFFF"/>',
    }
    for name, (bg, _) in services.items():
        text = "" if name != "twitter" else ""
        write(f"services/{name}.svg", svg(48, 48, f'''  <rect width="48" height="48" rx="14" fill="{bg}"/>
{inner.get(name, "")}'''))

    # 通用 platform / source 兜底图标
    write("services/source-generic.svg", svg(48, 48, f'''  <rect width="48" height="48" rx="14" fill="{SURFACE2}" stroke="{BORDER}"/>
  <path d="M16 20.5h16a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-7.2L21 35v-3.5h-5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2Z" fill="{PRIMARY}"/>'''))


# ============================================================================
# 03 · 国旗（内置 24 国，纯 SVG，无需外链）
# ============================================================================
# 用简化的准确旗面：条纹类用矩形拼接，复杂旗用近似几何
FLAGS = {
    "us": ('美国', ['#B22234', '#FFFFFF'], 'us'),
    "gb": ('英国', ['#012169', '#FFFFFF', '#C8102E'], 'gb'),
    "ca": ('加拿大', ['#D80621', '#FFFFFF'], 'ca'),
    "de": ('德国', ['#000000', '#DD0000', '#FFCE00'], 'de'),
    "fr": ('法国', ['#0055A4', '#FFFFFF', '#EF4135'], 'fr'),
    "jp": ('日本', ['#FFFFFF', '#BC002D'], 'jp'),
    "au": ('澳大利亚', ['#00247D', '#FFFFFF', '#FF0000'], 'au'),
    "sg": ('新加坡', ['#EF3340', '#FFFFFF'], 'sg'),
    "nl": ('荷兰', ['#AE1C28', '#FFFFFF', '#21468B'], 'nl'),
    "it": ('意大利', ['#009246', '#FFFFFF', '#CE2B37'], 'it'),
    "es": ('西班牙', ['#AA151B', '#F1BF00'], 'es'),
    "in": ('印度', ['#FF9933', '#FFFFFF', '#138808'], 'in'),
    "br": ('巴西', ['#009C3B', '#FFDF00', '#002776'], 'br'),
    "id": ('印尼', ['#FF0000', '#FFFFFF'], 'id'),
    "ph": ('菲律宾', ['#0038A8', '#CE1126', '#FFFFFF'], 'ph'),
    "ro": ('罗马尼亚', ['#002B7F', '#FCD116', '#CE1126'], 'ro'),
    "pl": ('波兰', ['#FFFFFF', '#DC143C'], 'pl'),
    "pr": ('波多黎各', ['#ED0000', '#FFFFFF', '#0050F0'], 'pr'),
    "ua": ('乌克兰', ['#0057B7', '#FFD700'], 'ua'),
    "se": ('瑞典', ['#006AA7', '#FECC00'], 'se'),
    "my": ('马来西亚', ['#010066', '#FFFFFF', '#CC0001'], 'my'),
    "mx": ('墨西哥', ['#006847', '#FFFFFF', '#CE1126'], 'mx'),
    "vn": ('越南', ['#DA251D', '#FFFF00'], 'vn'),
    "world": ('国际', ['#4F7FFF', '#2DD4A8'], 'world'),
}

W, H = 60, 40  # 3:2


def _hbar(colors, n):
    """水平等分条纹：用重叠矩形消除浮点缝隙，且不越界"""
    step = H / n
    out = []
    for i, col in enumerate(colors):
        y = i * step
        h = step + 0.6 if i < n - 1 else (H - y)   # 最后一条精确到底边
        out.append(f'<rect y="{y:.2f}" width="{W}" height="{h:.2f}" fill="{col}"/>')
    return "".join(out)


def _vbar(colors, n):
    """垂直等分条纹"""
    step = W / n
    out = []
    for i, col in enumerate(colors):
        x = i * step
        w = step + 0.6 if i < n - 1 else (W - x)
        out.append(f'<rect x="{x:.2f}" width="{w:.2f}" height="{H}" fill="{col}"/>')
    return "".join(out)


def _flag_body(code, kind, colors):
    c = colors
    if kind == "us":
        parts = [f'<rect width="{W}" height="{H}" fill="{c[1]}"/>']
        for i in range(7):
            parts.append(f'<rect y="{i*H/6.5:.2f}" width="{W}" height="{H/13:.2f}" fill="{c[0]}"/>')
        parts.append(f'<rect width="{W*0.44:.1f}" height="{H*0.54:.1f}" fill="#3C3B6E"/>')
        for r in range(5):
            for k in range(6):
                parts.append(f'<circle cx="{3+k*4.2:.1f}" cy="{3+r*4.2:.1f}" r="1" fill="#FFFFFF"/>')
        return "\n  ".join(parts)
    if kind == "gb":
        return (f'<rect width="{W}" height="{H}" fill="{c[0]}"/>'
                f'<path d="M0 0L{W} {H}M{W} 0L0 {H}" stroke="{c[1]}" stroke-width="8"/>'
                f'<path d="M0 0L{W} {H}M{W} 0L0 {H}" stroke="{c[2]}" stroke-width="4"/>'
                f'<path d="M{W/2} 0V{H}M0 {H/2}H{W}" stroke="{c[1]}" stroke-width="13"/>'
                f'<path d="M{W/2} 0V{H}M0 {H/2}H{W}" stroke="{c[2]}" stroke-width="7.5"/>')
    if kind == "ca":
        return (f'<rect width="{W}" height="{H}" fill="{c[1]}"/>'
                f'<rect width="{W*0.25}" height="{H}" fill="{c[0]}"/>'
                f'<rect x="{W*0.75}" width="{W*0.25}" height="{H}" fill="{c[0]}"/>'
                f'<path d="M30 9l2.4 4.2 4-1.2-1.6 4 3.2 2.6-4 1 .3 4-3.6-2.2-3.6 2.2.3-4-4-1 3.2-2.6-1.6-4 4 1.2L30 9Z" fill="{c[0]}"/>')
    if kind == "jp":
        return f'<rect width="{W}" height="{H}" fill="{c[0]}"/><circle cx="{W/2}" cy="{H/2}" r="{H*0.3:.1f}" fill="{c[1]}"/>'
    if kind == "de":
        return _hbar(c, 3)
    if kind == "fr":
        return _vbar(c, 3)
    if kind == "nl":
        return _hbar(c, 3)
    if kind == "it":
        return _vbar(c, 3)
    if kind == "ro":
        return _vbar(c, 3)
    if kind == "se":
        return (f'<rect width="{W}" height="{H}" fill="{c[0]}"/>'
                f'<rect x="{W*0.3:.1f}" width="{W*0.14:.1f}" height="{H}" fill="{c[1]}"/>'
                f'<rect y="{H*0.42:.1f}" width="{W}" height="{H*0.16:.1f}" fill="{c[1]}"/>')
    if kind == "au":
        return (f'<rect width="{W}" height="{H}" fill="{c[0]}"/>'
                f'<path d="M0 0L20 14M20 0L0 14" stroke="{c[1]}" stroke-width="3"/>'
                f'<path d="M10 0v14M0 7h20" stroke="{c[1]}" stroke-width="5"/>'
                f'<path d="M10 0v14M0 7h20" stroke="{c[2]}" stroke-width="2.6"/>'
                f'<circle cx="42" cy="10" r="2.6" fill="{c[1]}"/><circle cx="50" cy="20" r="1.8" fill="{c[1]}"/>'
                f'<circle cx="40" cy="28" r="1.8" fill="{c[1]}"/><circle cx="52" cy="33" r="1.6" fill="{c[1]}"/>')
    if kind == "sg":
        return (f'<rect width="{W}" height="{H/2:.1f}" fill="{c[0]}"/><rect y="{H/2:.1f}" width="{W}" height="{H/2:.1f}" fill="{c[1]}"/>'
                f'<circle cx="14" cy="10" r="6.5" fill="{c[1]}"/><circle cx="16.6" cy="10" r="6.2" fill="{c[0]}"/>'
                f'<circle cx="22" cy="7" r="1.1" fill="{c[1]}"/><circle cx="25" cy="11" r="1.1" fill="{c[1]}"/>'
                f'<circle cx="21.5" cy="14.6" r="1.1" fill="{c[1]}"/>')
    if kind == "es":
        return (f'<rect width="{W}" height="{H}" fill="{c[1]}"/>'
                f'<rect width="{W}" height="{H*0.25:.1f}" fill="{c[0]}"/>'
                f'<rect y="{H*0.75:.1f}" width="{W}" height="{H*0.25+0.4:.1f}" fill="{c[0]}"/>'
                f'<rect x="13" y="{H*0.36:.1f}" width="7" height="10" rx="1.6" fill="#AD1519"/>')
    if kind == "in":
        return (f'<rect width="{W}" height="{H/3:.1f}" fill="{c[0]}"/>'
                f'<rect y="{H/3:.1f}" width="{W}" height="{H/3:.1f}" fill="{c[1]}"/>'
                f'<rect y="{H*2/3:.1f}" width="{W}" height="{H/3+0.4:.1f}" fill="{c[2]}"/>'
                f'<circle cx="{W/2}" cy="{H/2}" r="5" fill="none" stroke="#000080" stroke-width="1.4"/>')
    if kind == "br":
        return (f'<rect width="{W}" height="{H}" fill="{c[0]}"/>'
                f'<path d="M30 5L55 20 30 35 5 20Z" fill="{c[1]}"/>'
                f'<circle cx="30" cy="20" r="8.5" fill="{c[2]}"/>')
    if kind == "id":
        return _hbar(c, 2)
    if kind == "pl":
        return _hbar(c, 2)
    if kind == "ua":
        return _hbar(c, 2)
    if kind == "ph":
        return (f'<rect width="{W}" height="{H/2:.1f}" fill="{c[0]}"/><rect y="{H/2:.1f}" width="{W}" height="{H/2:.1f}" fill="{c[1]}"/>'
                f'<path d="M0 0L24 20 0 40Z" fill="{c[2]}"/>'
                f'<circle cx="9" cy="20" r="3.4" fill="#FCD116"/>')
    if kind == "pr":
        parts = [f'<rect width="{W}" height="{H}" fill="{c[1]}"/>']
        for i in range(5):
            parts.append(f'<rect y="{i*H/5:.2f}" width="{W}" height="{H/10:.2f}" fill="{c[0]}"/>')
        parts.append(f'<path d="M0 0L26 20 0 40Z" fill="{c[2]}"/>')
        parts.append('<circle cx="9" cy="20" r="3.2" fill="#FFFFFF"/>')
        return "".join(parts)
    if kind == "my":
        parts = [f'<rect width="{W}" height="{H}" fill="{c[1]}"/>']
        for i in range(7):
            parts.append(f'<rect y="{i*H/7:.2f}" width="{W}" height="{H/14:.2f}" fill="{c[2]}"/>')
        parts.append(f'<rect width="{W*0.5:.1f}" height="{H*0.57:.1f}" fill="{c[0]}"/>')
        parts.append('<circle cx="13" cy="11" r="5" fill="#FFCC00"/><circle cx="15.4" cy="11" r="4.6" fill="#010066"/>')
        return "".join(parts)
    if kind == "mx":
        return (_vbar(c, 3)[:-0] if False else
                f'<rect width="{W/3:.1f}" height="{H}" fill="{c[0]}"/>'
                f'<rect x="{W/3:.1f}" width="{W/3:.1f}" height="{H}" fill="{c[1]}"/>'
                f'<rect x="{W*2/3:.1f}" width="{W/3+0.4:.1f}" height="{H}" fill="{c[2]}"/>'
                f'<circle cx="30" cy="20" r="4.6" fill="none" stroke="#8B5A2B" stroke-width="1.6"/>')
    if kind == "vn":
        return (f'<rect width="{W}" height="{H}" fill="{c[0]}"/>'
                f'<path d="M30 11l2.6 8h8.4l-6.8 5 2.6 8-6.8-5-6.8 5 2.6-8-6.8-5h8.4L30 11Z" fill="{c[1]}"/>')
    if kind == "world":
        return (f'<rect width="{W}" height="{H}" rx="6" fill="#101722" stroke="rgba(255,255,255,.12)"/>'
                f'<circle cx="30" cy="20" r="11" fill="none" stroke="#4F7FFF" stroke-width="1.6"/>'
                f'<path d="M19 20h22M30 9c3 3.2 4.6 7 4.6 11S33 28 30 31s-4.6-7-4.6-11S27 12.2 30 9Z" stroke="#2DD4A8" stroke-width="1.4" fill="none"/>')
    return f'<rect width="{W}" height="{H}" fill="{c[0]}"/>'


def gen_flags():
    for code, (cn, colors, kind) in FLAGS.items():
        body = _flag_body(code, kind, colors)
        write(f"flags/{code}.svg", svg(W, H, f'''  <g clip-path="url(#clip_{code})">
  {body}
  </g>
  <defs><clipPath id="clip_{code}"><rect width="{W}" height="{H}" rx="{4 if kind!='world' else 6}"/></clipPath></defs>
  <rect width="{W}" height="{H}" rx="{4 if kind!='world' else 6}" fill="none" stroke="rgba(255,255,255,.16)"/>'''))

    # manifest 便于前端按国家码取图
    lines = ["# 国旗素材清单（3:2，60×40）", "", "| code | 国家 | 文件 |", "| --- | --- | --- |"]
    for code, (cn, _, _) in FLAGS.items():
        lines.append(f"| {code} | {cn} | `flags/{code}.svg` |")
    write("flags/README.md", "\n".join(lines))


# ============================================================================
# 06/07 · phone / functions 补充
# ============================================================================
def gen_misc():
    # 07 · 功能图标（带底色容器，用于功能宫格）
    fns = {
        "search": ("搜索", ICONS["search"]),
        "filter": ("筛选", ICONS["filter"]),
        "refresh": ("刷新", ICONS["refresh"]),
        "copy": ("复制", ICONS["copy"]),
        "external-link": ("打开链接", ICONS["external-link"]),
        "message": ("短信", ICONS["message"]),
        "inbox": ("收件箱", ICONS["inbox"]),
        "phone": ("手机", ICONS["phone"]),
        "globe": ("国家", ICONS["globe"]),
        "home": ("首页", ICONS["home"]),
        "star": ("推荐", ICONS["star"]),
        "swap": ("换号", ICONS["swap"]),
        "bell": ("通知", ICONS["bell"]),
        "settings": ("设置", ICONS["settings"]),
        "help": ("帮助", ICONS["help"]),
        "guide": ("指南", ICONS["guide"]),
        "shield": ("安全", ICONS["shield"]),
        "status-unknown": ("等待中", '<circle cx="12" cy="12" r="8.4"/>'),
    }
    for name, (label, body) in fns.items():
        b = body.replace("__ACCENT__", ACCENT).replace("__MUTED__", MUTED).replace("__PRIMARY__", PRIMARY)
        b = b.replace("><", ">\n      <")
        write(f"functions/fn-{name}.svg", svg(72, 92, f'''  <rect x="12" y="4" width="48" height="48" rx="14" fill="{PRIMARY}" fill-opacity=".10" stroke="{BORDER}"/>
  <g transform="translate(24 16)" fill="none" stroke="{PRIMARY}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      {b}
  </g>
  <text x="36" y="76" fill="{TEXT}" font-size="12" font-weight="600" text-anchor="middle" font-family="{FONT}">{label}</text>'''))


# ============================================================================
# 主流程
# ============================================================================
def main():
    gen_brand()
    gen_hero()
    gen_elements()
    gen_status()
    gen_badges()
    gen_usp()
    gen_empty()
    gen_icons()
    gen_services()
    gen_flags()
    gen_misc()

    print(f"输出目录：{ROOT}")
    print(f"共生成 {len(_written)} 个文件：")
    cur = None
    for rel in _written:
        d = os.path.dirname(rel)
        if d != cur:
            print(f"  [{d or '.'}]")
            cur = d
        print(f"    {os.path.basename(rel)}")


if __name__ == "__main__":
    main()

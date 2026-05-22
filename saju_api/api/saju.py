#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler
import argparse
import datetime
import io
import json
import math
import sys
from typing import Any, Dict, List, Optional

MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]
MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
EL_EN = {'목': 'Wood', '화': 'Fire', '토': 'Earth', '금': 'Metal', '수': 'Water'}

SPECIAL_SAL_META = [
    {'key': 'cheonul', 'ko': '天乙貴人', 'hanja': '천을귀인', 'en': 'Heavenly Guardian', 'indexed': True},
    {'key': 'cheonduk', 'ko': '天德貴人', 'hanja': '천덕귀인', 'en': 'Heaven Virtue Star', 'indexed': True},
    {'key': 'wolduk', 'ko': '月德貴人', 'hanja': '월덕귀인', 'en': 'Month Virtue Star', 'indexed': True},
    {'key': 'munchang', 'ko': '文昌貴人', 'hanja': '문창귀인', 'en': 'Literary Star', 'indexed': True},
    {'key': 'yangin', 'ko': '陽刃', 'hanja': '양인', 'en': 'Yang Blade', 'indexed': True},
    {'key': 'dohwa', 'ko': '桃花', 'hanja': '도화', 'en': 'Peach Blossom', 'indexed': True},
    {'key': 'geumyeo', 'ko': '金輿', 'hanja': '금여', 'en': 'Golden Carriage', 'indexed': True},
    {'key': 'baekho', 'ko': '白虎', 'hanja': '백호', 'en': 'White Tiger (Day Master)', 'indexed': False},
    {'key': 'goegang', 'ko': '魁罡', 'hanja': '괴강', 'en': 'Goegang (Day Master)', 'indexed': False},
    {'key': 'hongyeom', 'ko': '紅艶', 'hanja': '홍염', 'en': 'Red Flame (Day Master)', 'indexed': False},
]

OHAENG = {
    '甲': '목', '乙': '목', '丙': '화', '丁': '화', '戊': '토', '己': '토',
    '庚': '금', '辛': '금', '壬': '수', '癸': '수',
    '寅': '목', '卯': '목', '巳': '화', '午': '화',
    '辰': '토', '戌': '토', '丑': '토', '未': '토',
    '申': '금', '酉': '금', '亥': '수', '子': '수',
}

RELTYPE_EN = {
    '合': 'Combine', '沖': 'Clash', '破': 'Break', '害': 'Harm', '刑': 'Punish',
    '元嗔': 'Resent', '鬼門': 'GhostGate', '半合': 'Half-Combine',
    '三合': 'Triple', '方合': 'Directional',
}
SIPSIN_EN = {
    '比肩': 'Friend', '劫財': 'Rob Wealth', '食神': 'Food God', '傷官': 'Hurt Officer',
    '偏財': 'Indirect Wealth', '正財': 'Direct Wealth', '偏官': '7 Killings',
    '正官': 'Direct Officer', '偏印': 'Indirect Resource', '正印': 'Direct Resource',
}
METEOR_EN = {
    '長生': 'Birth', '沐浴': 'Bathing', '冠帶': 'Dressing', '乾祿': 'Fullness',
    '帝旺': 'Peak', '衰': 'Decline', '病': 'Illness', '死': 'Death',
    '墓': 'Tomb', '絶': 'Void', '胎': 'Womb', '養': 'Nurture',
}
SPIRIT_EN = {
    '劫殺': 'Rob', '災殺': 'Disaster', '天殺': 'Heaven', '地殺': 'Earth',
    '年殺': 'Year', '月殺': 'Month', '亡身': 'Loss', '將星': 'General',
    '攀鞍': 'Saddle', '驛馬': 'Travel', '六害': 'Harm', '華蓋': 'Canopy',
}

SKY = '甲乙丙丁戊己庚辛壬癸'
EARTH = '子丑寅卯辰巳午未申酉戌亥'
SKY_KR = '갑을병정무기경신임계'
EARTH_KR = '자축인묘진사오미신유술해'
YANGGAN = ['甲', '丙', '戊', '庚', '壬']
CHANGSAENG_START = {
    '甲': '亥', '乙': '午', '丙': '寅', '丁': '酉',
    '戊': '寅', '己': '酉', '庚': '巳', '辛': '子',
    '壬': '申', '癸': '卯',
}
RELATIONS = [
    {'hanja': '比肩', 'hangul': '비겁'},
    {'hanja': '劫財', 'hangul': '겁재'},
    {'hanja': '食神', 'hangul': '식신'},
    {'hanja': '傷官', 'hangul': '상관'},
    {'hanja': '偏財', 'hangul': '편재'},
    {'hanja': '正財', 'hangul': '정재'},
    {'hanja': '偏官', 'hangul': '편관'},
    {'hanja': '正官', 'hangul': '정관'},
    {'hanja': '偏印', 'hangul': '편인'},
    {'hanja': '正印', 'hangul': '정인'},
]
METEORS_12 = [
    {'hanja': '長生', 'hangul': '장생'},
    {'hanja': '沐浴', 'hangul': '목욕'},
    {'hanja': '冠帶', 'hangul': '관대'},
    {'hanja': '乾祿', 'hangul': '건록'},
    {'hanja': '帝旺', 'hangul': '제왕'},
    {'hanja': '衰', 'hangul': '쇠'},
    {'hanja': '病', 'hangul': '병'},
    {'hanja': '死', 'hangul': '사'},
    {'hanja': '墓', 'hangul': '묘'},
    {'hanja': '絶', 'hangul': '절'},
    {'hanja': '胎', 'hangul': '태'},
    {'hanja': '養', 'hangul': '양'},
]
SPIRITS_12 = [
    {'hanja': '劫殺', 'hangul': '겁살'},
    {'hanja': '災殺', 'hangul': '재살'},
    {'hanja': '天殺', 'hangul': '천살'},
    {'hanja': '地殺', 'hangul': '지살'},
    {'hanja': '年殺', 'hangul': '년살'},
    {'hanja': '月殺', 'hangul': '월살'},
    {'hanja': '亡身', 'hangul': '망신'},
    {'hanja': '將星', 'hangul': '장성'},
    {'hanja': '攀鞍', 'hangul': '반안'},
    {'hanja': '驛馬', 'hangul': '역마'},
    {'hanja': '六害', 'hangul': '육해'},
    {'hanja': '華蓋', 'hangul': '화개'},
]
BRANCH_ELEMENT = {
    '寅': 'tree', '卯': 'tree', '巳': 'fire', '午': 'fire',
    '辰': 'earth', '戌': 'earth', '丑': 'earth', '未': 'earth',
    '申': 'metal', '酉': 'metal', '子': 'water', '亥': 'water',
}
STEM_INFO = {
    '甲': {'yinyang': '+', 'element': 'tree'},
    '乙': {'yinyang': '-', 'element': 'tree'},
    '丙': {'yinyang': '+', 'element': 'fire'},
    '丁': {'yinyang': '-', 'element': 'fire'},
    '戊': {'yinyang': '+', 'element': 'earth'},
    '己': {'yinyang': '-', 'element': 'earth'},
    '庚': {'yinyang': '+', 'element': 'metal'},
    '辛': {'yinyang': '-', 'element': 'metal'},
    '壬': {'yinyang': '+', 'element': 'water'},
    '癸': {'yinyang': '-', 'element': 'water'},
}
TRIPLE_COMPOSES = [
    ['巳', '午', '辰'],
    ['亥', '酉', '丑'],
    ['申', '子', '戌'],
    ['卯', '未', '寅'],
]
TRIPLE_COMPOSE_ELEMENTS = {
    '巳,午,辰': 'fire',
    '亥,酉,丑': 'metal',
    '申,子,戌': 'water',
    '卯,未,寅': 'tree',
}
HALF_COMPOSES = {
    '寅,午': ['半合', 'fire'],
    '午,辰': ['半合', 'fire'],
    '亥,酉': ['半合', 'metal'],
    '酉,丑': ['半合', 'metal'],
    '申,子': ['半合', 'water'],
    '子,戌': ['半合', 'water'],
    '卯,未': ['半合', 'tree'],
    '未,辰': ['半合', 'tree'],
}
DIRECTIONAL_COMPOSES = [
    ['寅', '巳', '戌'],
    ['亥', '午', '未'],
    ['申', '酉', '辰'],
    ['卯', '子', '丑'],
]
DIRECTIONAL_COMPOSE_ELEMENTS = {
    '寅,巳,戌': 'tree',
    '亥,午,未': 'fire',
    '申,酉,辰': 'metal',
    '卯,子,丑': 'water',
}
STEM_COMBINES = {
    '甲,己': ['合', 'earth'],
    '乙,庚': ['合', 'metal'],
    '丙,辛': ['合', 'water'],
    '丁,壬': ['合', 'tree'],
    '戊,癸': ['合', 'fire'],
}
STEM_CLASHES = {
    '甲,庚': '沖',
    '乙,辛': '沖',
    '丙,壬': '沖',
    '丁,癸': '沖',
}
BRANCH_COMBINES_6 = {
    '子,丑': ['合', 'earth'],
    '寅,卯': ['合', 'tree'],
    '巳,午': ['合', 'fire'],
    '申,酉': ['合', 'metal'],
    '亥,辰': ['合', 'water'],
    '午,未': ['合', 'fire'],
}
BRANCH_CLASHES = {
    '子,午': '沖', '亥,未': '沖', '寅,申': '沖', '卯,酉': '沖', '辰,戌': '沖', '巳,丑': '沖'
}
BRANCH_BREAKS = {
    '子,酉': '破', '丑,申': '破', '寅,巳': '破', '卯,午': '破', '辰,亥': '破', '未,戌': '破'
}
BRANCH_HARMS = {
    '子,辰': '害', '丑,午': '害', '寅,巳': '害', '卯,戌': '害', '申,亥': '害', '酉,未': '害'
}
BRANCH_PUNISHMENTS = {
    '寅,巳': ['刑', '無恩'], '巳,寅': ['刑', '無恩'],
    '申,亥': ['刑', '無恩'], '亥,申': ['刑', '無恩'],
    '午,丑': ['刑', '無禮'], '丑,午': ['刑', '無禮'],
    '辰,子': ['刑', '相刑'], '子,辰': ['刑', '相刑'],
}
BRANCH_SELF_PUNISHMENTS = {'戌', '午', '酉', '子'}
BRANCH_WONJIN = {
    '子,辰': '怨嗔', '丑,午': '怨嗔', '寅,戌': '怨嗔', '卯,未': '怨嗔', '申,辰': '怨嗔', '酉,丑': '怨嗔'
}
BRANCH_GWIMUN = {
    '子,申': '鬼門', '丑,未': '鬼門', '寅,午': '鬼門', '卯,酉': '鬼門', '辰,亥': '鬼門', '巳,戌': '鬼門'
}
YANGIN_MAP = {'甲': '巳', '丙': '午', '戊': '午', '庚': '酉', '壬': '子'}
BAEKHO_PILLARS = {'甲戌', '乙未', '丙辰', '丁丑', '戊戌', '己辰', '庚寅'}
GOEGANG_PILLARS = {'庚戌', '庚辰', '壬戌', '戊戌'}
DOHWA_MAP = {
    '寅': '亥', '卯': '亥', '巳': '亥',
    '申': '子', '酉': '子', '戌': '子',
    '亥': '午', '子': '午', '丑': '午',
    '辰': '寅', '巳': '寅', '未': '寅'
}
CHEONUL_MAP = {
    '甲': ['亥', '未'], '戊': ['亥', '未'], '庚': ['亥', '未'],
    '乙': ['子', '申'], '己': ['子', '申'],
    '丙': ['卯', '酉'], '丁': ['卯', '酉'],
    '辛': ['午', '寅'], '壬': ['巳', '亥'], '癸': ['巳', '亥'],
}
CHEONDUK_MAP = {
    '巳': '丁', '午': '乙', '亥': '辛', '子': '壬', '卯': '癸', '辰': '乙',
    '未': '甲', '申': '癸', '酉': '丙', '戌': '己', '丑': '丁', '寅': '戊'
}
WOLDUK_MAP = {
    '巳': '丙', '午': '丙', '辰': '丙', '申': '壬', '酉': '壬', '戌': '壬',
    '亥': '庚', '子': '庚', '丑': '庚', '寅': '甲', '卯': '甲', '未': '甲'
}
MUNCHANG_MAP = {'甲': '丑', '乙': '午', '丙': '酉', '丁': '亥', '戊': '寅', '己': '卯', '庚': '未', '辛': '子', '壬': '辰', '癸': '巳'}
HONGYEOM_PILLARS = {'甲午', '丙辰', '丁未', '戊戌', '庚申', '辛酉', '壬子'}
GEUMYEO_MAP = {'甲': '酉', '乙': '子', '丙': '未', '丁': '亥', '戊': '未', '己': '亨', '庚': '巳', '辛': '卯', '壬': '丑', '癸': '巳'}
JIJANGGAN = {
    '寅': '丙丁甲', '卯': '甲 乙', '辰': '乙癸戊',
    '巳': '戊庚丙', '午': '丙丁己', '未': '己乙丁',
    '申': '戊壬庚', '酉': '庚 辛', '戌': '辛丁戊',
    '亥': '壬甲癸', '子': '癸 甲', '丑': '辛癸己',
}
GONGMANG_TABLE = [
    ['巳', '亥'],
    ['申', '酉'],
    ['午', '未'],
    ['寅', '卯'],
    ['子', '丑'],
    ['辰', '戌'],
]
HGANJI = [
    '甲子', '乙丑', '丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉',
    '甲戌', '乙亥', '丙子', '丁丑', '戊寅', '己卯', '庚辰', '辛巳', '壬午', '癸未',
    '甲申', '乙酉', '丙戌', '丁亥', '戊子', '己丑', '庚寅', '辛卯', '壬辰', '癸巳',
    '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑', '壬寅', '癸卯',
    '甲辰', '乙巳', '丙午', '丁未', '戊申', '己酉', '庚戌', '辛亥', '壬子', '癸丑',
    '甲寅', '乙卯', '丙辰', '丁巳', '戊午', '己未', '庚申', '辛酉', '壬戌', '癸亥',
]
MONTH = [
    0, 21355, 42843, 64498, 86335, 108366, 130578, 152958, 175471, 198077,
    220728, 243370, 265955, 288432, 310767, 332928, 354903, 376685, 398290,
    419736, 441060, 462295, 483493, 504693, 525949,
]
UNIT = {
    'year': 1996,
    'month': 2,
    'day': 4,
    'hour': 22,
    'min': 8,
    'ygan': 2,
    'yji': 0,
    'mgan': 6,
    'mji': 2,
    'msu': 26,
    'dgan': 7,
    'dji': 7,
    'dsu': 7,
    'hgan': 5,
    'hji': 11,
    'hsu': 35,
}


def trunc_div(a: int, b: int) -> int:
    return int(a / b)


def adjust_kdt_to_kst(year: int, month: int, day: int, hour: int, minute: int) -> Dict[str, int]:
    if not is_korean_daylight_time(year, month, day):
        return {'year': year, 'month': month, 'day': day, 'hour': hour, 'minute': minute}
    hour -= 1
    if hour < 0:
        hour += 24
        d = datetime.date(year, month, day) - datetime.timedelta(days=1)
        year, month, day = d.year, d.month, d.day
    return {'year': year, 'month': month, 'day': day, 'hour': hour, 'minute': minute}


def is_korean_daylight_time(year: int, month: int, day: int) -> bool:
    if year == 1987:
        return (month > 5 and month < 10) or (month == 5 and day >= 10) or (month == 10 and day <= 11)
    if year == 1988:
        return (month > 5 and month < 10) or (month == 5 and day >= 8) or (month == 10 and day <= 9)
    return False


def minutes_between(uyear: int, umonth: int, uday: int, uhour: int, umin: int, y1: int, mo1: int, d1: int, h1: int, mm1: int) -> int:
    a = datetime.datetime(uyear, umonth, uday, uhour, umin)
    b = datetime.datetime(y1, mo1, d1, h1, mm1)
    return int((a - b).total_seconds() / 60)


def date_from_minutes(tmin: int, uyear: int, umonth: int, uday: int, uhour: int, umin: int) -> List[int]:
    origin = datetime.datetime(uyear, umonth, uday, uhour, umin)
    target = origin + datetime.timedelta(minutes=tmin)
    return [target.year, target.month, target.day, target.hour, target.minute]


def calc_pillar_indices(year: int, month: int, day: int, hour: int, minute: int, jasi_method: Optional[str] = None) -> List[int]:
    displ2min = minutes_between(UNIT['year'], UNIT['month'], UNIT['day'], UNIT['hour'], UNIT['min'], year, month, day, hour, minute)
    displ2day = (datetime.date(year, month, day) - datetime.date(UNIT['year'], UNIT['month'], UNIT['day'])).days
    so24 = trunc_div(displ2min, 525949)
    if displ2min >= 0:
        so24 += 1
    so24year = so24 % 60 * -1 + 12
    if so24year < 0:
        so24year += 60
    elif so24year > 59:
        so24year -= 60
    monthmin100 = displ2min % 525949
    monthmin100 = 525949 - monthmin100
    if monthmin100 < 0:
        monthmin100 += 525949
    elif monthmin100 >= 525949:
        monthmin100 -= 525949
    so24month_idx = 0
    for i2 in range(12):
        j = i2 * 2
        if MONTH[j] <= monthmin100 < MONTH[j + 2]:
            so24month_idx = i2
    t = so24year % 10
    t = t % 5
    t = t * 12 + 2 + so24month_idx
    so24month = t
    if so24month > 59:
        so24month -= 60
    so24day = displ2day % 60
    so24day = so24day * -1 + 7
    if so24day < 0:
        so24day += 60
    elif so24day > 59:
        so24day -= 60
    i = 0
    if hour == 0 or (hour == 1 and minute < 30):
        i = 0
    elif (hour == 1 and minute >= 30) or hour == 2 or (hour == 3 and minute < 30):
        i = 1
    elif (hour == 3 and minute >= 30) or hour == 4 or (hour == 5 and minute < 30):
        i = 2
    elif (hour == 5 and minute >= 30) or hour == 6 or (hour == 7 and minute < 30):
        i = 3
    elif (hour == 7 and minute >= 30) or hour == 8 or (hour == 9 and minute < 30):
        i = 4
    elif (hour == 9 and minute >= 30) or hour == 10 or (hour == 11 and minute < 30):
        i = 5
    elif (hour == 11 and minute >= 30) or hour == 12 or (hour == 13 and minute < 30):
        i = 6
    elif (hour == 13 and minute >= 30) or hour == 14 or (hour == 15 and minute < 30):
        i = 7
    elif (hour == 15 and minute >= 30) or hour == 16 or (hour == 17 and minute < 30):
        i = 8
    elif (hour == 17 and minute >= 30) or hour == 18 or (hour == 19 and minute < 30):
        i = 9
    elif (hour == 19 and minute >= 30) or hour == 20 or (hour == 21 and minute < 30):
        i = 10
    elif (hour == 21 and minute >= 30) or hour == 22 or (hour == 23 and minute < 30):
        i = 11
    else:
        i = 0
        method = jasi_method or 'unified'
        if method == 'unified':
            so24day += 1
            if so24day == 60:
                so24day = 0
    is_yajasi = i == 0 and hour == 23 and jasi_method == 'split'
    day_for_hour = (so24day + 1) % 60 if is_yajasi else so24day
    t = day_for_hour % 10
    t = t % 5
    t = t * 12 + i
    so24hour = t
    return [so24, so24year, so24month, so24day, so24hour]


def calc_solar_terms(year: int, month: int, day: int, hour: int, minute: int, jasi_method: Optional[str] = None) -> Dict[str, int]:
    _, _, so24month, _, _ = calc_pillar_indices(year, month, day, hour, minute, jasi_method)
    displ2min = minutes_between(UNIT['year'], UNIT['month'], UNIT['day'], UNIT['hour'], UNIT['min'], year, month, day, hour, minute)
    monthmin100 = (-displ2min) % 525949
    if monthmin100 < 0:
        monthmin100 += 525949
    elif monthmin100 >= 525949:
        monthmin100 -= 525949
    ii = so24month % 12 - 2
    if ii == -2:
        ii = 10
    elif ii == -1:
        ii = 11
    ingi_name = ii * 2
    mid_name = ii * 2 + 1
    outgi_name = ii * 2 + 2
    j = ii * 2
    tmin = -displ2min + (monthmin100 - MONTH[j])
    ingi_year, ingi_month, ingi_day, ingi_hour, ingi_min = date_from_minutes(tmin, UNIT['year'], UNIT['month'], UNIT['day'], UNIT['hour'], UNIT['min'])
    tmin = -displ2min + (monthmin100 - MONTH[j + 1])
    mid_year, mid_month, mid_day, mid_hour, mid_min = date_from_minutes(tmin, UNIT['year'], UNIT['month'], UNIT['day'], UNIT['hour'], UNIT['min'])
    tmin = -displ2min + (monthmin100 - MONTH[j + 2])
    outgi_year, outgi_month, outgi_day, outgi_hour, outgi_min = date_from_minutes(tmin, UNIT['year'], UNIT['month'], UNIT['day'], UNIT['hour'], UNIT['min'])
    return {
        'ingiName': ingi_name,
        'ingiYear': ingi_year,
        'ingiMonth': ingi_month,
        'ingiDay': ingi_day,
        'ingiHour': ingi_hour,
        'ingiMin': ingi_min,
        'midName': mid_name,
        'midYear': mid_year,
        'midMonth': mid_month,
        'midDay': mid_day,
        'midHour': mid_hour,
        'midMin': mid_min,
        'outgiName': outgi_name,
        'outgiYear': outgi_year,
        'outgiMonth': outgi_month,
        'outgiDay': outgi_day,
        'outgiHour': outgi_hour,
        'outgiMin': outgi_min,
    }


def get_four_pillars(year: int, month: int, day: int, hour: int, minute: int, jasi_method: Optional[str] = None) -> List[str]:
    _, sy, sm, sd, sh = calc_pillar_indices(year, month, day, hour, minute, jasi_method)
    return [HGANJI[sy], HGANJI[sm], HGANJI[sd], HGANJI[sh]]


def get_daewoon(is_male: bool, year: int, month: int, day: int, hour: int, minute: int, jasi_method: Optional[str] = None) -> List[Dict[str, Any]]:
    _, sy, sm, _, _ = calc_pillar_indices(year, month, day, hour, minute, jasi_method)
    year_stem = HGANJI[sy][0]
    is_yang_gan = year_stem in YANGGAN
    order = (is_male and is_yang_gan) or (not is_male and not is_yang_gan)
    terms = calc_solar_terms(year, month, day, hour, minute, jasi_method)
    if order:
        d0 = datetime.datetime(terms['outgiYear'], terms['outgiMonth'], terms['outgiDay'], terms['outgiHour'], terms['outgiMin'])
    else:
        d0 = datetime.datetime(terms['ingiYear'], terms['ingiMonth'], terms['ingiDay'], terms['ingiHour'], terms['ingiMin'])
    birth = datetime.datetime(year, month, day, hour, minute)
    diff = birth - d0
    seconds_to_first = abs(diff.total_seconds()) * 365.242196 / 3
    next_date = birth + datetime.timedelta(seconds=seconds_to_first)
    next_date = next_date.replace(microsecond=0)
    flow = 1 if order else -1
    m_idx = sm
    result = []
    for i in range(10):
        m_idx += flow
        if m_idx >= len(HGANJI):
            m_idx = 0
        if m_idx < 0:
            m_idx = len(HGANJI) - 1
        result.append({'ganzi': HGANJI[m_idx], 'startDate': next_date})
        next_date = next_date.replace(year=next_date.year + 10)
    return result


def get_interaction(e0: str, e1: str) -> Optional[str]:
    if e0 == e1:
        return 'same'
    if (e0 == 'water' and e1 == 'tree') or (e0 == 'tree' and e1 == 'fire') or (e0 == 'fire' and e1 == 'earth') or (e0 == 'earth' and e1 == 'metal') or (e0 == 'metal' and e1 == 'water'):
        return 'output'
    if (e0 == 'water' and e1 == 'metal') or (e0 == 'tree' and e1 == 'water') or (e0 == 'fire' and e1 == 'tree') or (e0 == 'earth' and e1 == 'fire') or (e0 == 'metal' and e1 == 'earth'):
        return 'input'
    if (e0 == 'water' and e1 == 'earth') or (e0 == 'tree' and e1 == 'metal') or (e0 == 'fire' and e1 == 'water') or (e0 == 'earth' and e1 == 'tree') or (e0 == 'metal' and e1 == 'fire'):
        return 'shield'
    if (e0 == 'water' and e1 == 'fire') or (e0 == 'tree' and e1 == 'earth') or (e0 == 'fire' and e1 == 'metal') or (e0 == 'earth' and e1 == 'water') or (e0 == 'metal' and e1 == 'tree'):
        return 'sword'
    return None


def get_relation(day_stem: str, target_stem: str) -> Optional[Dict[str, str]]:
    day = STEM_INFO.get(day_stem)
    target = STEM_INFO.get(target_stem)
    if not day or not target:
        return None
    interaction = get_interaction(day['element'], target['element'])
    if interaction is None:
        return None
    same_yy = day['yinyang'] == target['yinyang']
    if interaction == 'same':
        return RELATIONS[0] if same_yy else RELATIONS[1]
    if interaction == 'output':
        return RELATIONS[2] if same_yy else RELATIONS[3]
    if interaction == 'sword':
        return RELATIONS[4] if same_yy else RELATIONS[5]
    if interaction == 'shield':
        return RELATIONS[6] if same_yy else RELATIONS[7]
    if interaction == 'input':
        return RELATIONS[8] if same_yy else RELATIONS[9]
    return None


def get_hidden_stems(branch: str) -> str:
    return JIJANGGAN.get(branch, '')


def get_jeonggi(branch: str) -> str:
    return get_hidden_stems(branch).replace(' ', '')[-1:] if branch else ''


def to_hangul(hanja: str) -> str:
    sky_idx = SKY.find(hanja)
    if sky_idx >= 0:
        return SKY_KR[sky_idx]
    earth_idx = EARTH.find(hanja)
    if earth_idx >= 0:
        return EARTH_KR[earth_idx]
    return hanja


def get_twelve_meteor(stem: str, branch: str) -> str:
    start = CHANGSAENG_START.get(stem)
    if not start:
        return '?'
    start_idx = EARTH.find(start)
    branch_idx = EARTH.find(branch)
    if start_idx < 0 or branch_idx < 0:
        return '?'
    stage = (branch_idx - start_idx) % 12 if stem in YANGGAN else (start_idx - branch_idx) % 12
    return METEORS_12[stage]['hanja']


SPIRIT_START = {
    '寅': 11, '午': 11, '戌': 11,
    '巳': 2,  '酉': 2,  '丑': 2,
    '申': 5,  '子': 5,  '辰': 5,
    '亥': 8,  '卯': 8,  '未': 8,
}


def get_twelve_spirit(year_branch: str, target_branch: str) -> str:
    start = SPIRIT_START.get(year_branch)
    if start is None:
        return '?'
    target_idx = EARTH.find(target_branch)
    if target_idx < 0:
        return '?'
    offset = ((target_idx - start) % 12 + 12) % 12
    return SPIRITS_12[offset]['hanja']


def lookup_pair(table: Dict[str, Any], a: str, b: str) -> Any:
    return table.get(f'{a},{b}') or table.get(f'{b},{a}')


def get_stem_relation(stem1: str, stem2: str) -> List[Dict[str, Optional[str]]]:
    results = []
    combine = lookup_pair(STEM_COMBINES, stem1, stem2)
    if combine:
        results.append({'type': combine[0], 'detail': combine[1]})
    clash = lookup_pair(STEM_CLASHES, stem1, stem2)
    if clash:
        results.append({'type': clash, 'detail': None})
    return results


def get_branch_relation(branch1: str, branch2: str) -> List[Dict[str, Optional[str]]]:
    results = []
    combine = lookup_pair(BRANCH_COMBINES_6, branch1, branch2)
    if combine:
        results.append({'type': combine[0], 'detail': combine[1]})
    half = lookup_pair(HALF_COMPOSES, branch1, branch2)
    if half:
        results.append({'type': half[0], 'detail': half[1]})
    clash = lookup_pair(BRANCH_CLASHES, branch1, branch2)
    if clash:
        results.append({'type': clash, 'detail': None})
    brk = lookup_pair(BRANCH_BREAKS, branch1, branch2)
    if brk:
        results.append({'type': brk, 'detail': None})
    harm = lookup_pair(BRANCH_HARMS, branch1, branch2)
    if harm:
        results.append({'type': harm, 'detail': None})
    punishment = BRANCH_PUNISHMENTS.get(f'{branch1},{branch2}') or BRANCH_PUNISHMENTS.get(f'{branch2},{branch1}')
    if punishment:
        results.append({'type': punishment[0], 'detail': punishment[1]})
    if branch1 == branch2 and branch1 in BRANCH_SELF_PUNISHMENTS:
        results.append({'type': '刑', 'detail': '自刑'})
    wonjin = lookup_pair(BRANCH_WONJIN, branch1, branch2)
    if wonjin:
        results.append({'type': wonjin, 'detail': None})
    gwimun = lookup_pair(BRANCH_GWIMUN, branch1, branch2)
    if gwimun:
        results.append({'type': gwimun, 'detail': None})
    return results


def analyze_pillar_relations(pillar1: List[str], pillar2: List[str]) -> Dict[str, List[Dict[str, Optional[str]]]]:
    return {'stem': get_stem_relation(pillar1[0], pillar2[0]), 'branch': get_branch_relation(pillar1[1], pillar2[1])}


def check_triple_compose(branches: List[str]) -> List[Dict[str, str]]:
    results = []
    branch_set = set(branches)
    for triple in TRIPLE_COMPOSES:
        if set(triple).issubset(branch_set):
            key = ','.join(triple)
            results.append({'type': '三合', 'detail': TRIPLE_COMPOSE_ELEMENTS[key]})
    return results


def check_directional_compose(branches: List[str]) -> List[Dict[str, str]]:
    results = []
    branch_set = set(branches)
    for dir_combo in DIRECTIONAL_COMPOSES:
        if set(dir_combo).issubset(branch_set):
            key = ','.join(dir_combo)
            results.append({'type': '方合', 'detail': DIRECTIONAL_COMPOSE_ELEMENTS[key]})
    return results


def analyze_all_relations(pillars: List[List[str]]) -> Dict[str, Any]:
    pairs: Dict[str, Any] = {}
    for i in range(len(pillars)):
        for j in range(i + 1, len(pillars)):
            rel = analyze_pillar_relations(pillars[i], pillars[j])
            if rel['stem'] or rel['branch']:
                pairs[f'{i},{j}'] = rel
    branches = [p[1] for p in pillars]
    return {'pairs': pairs, 'triple': check_triple_compose(branches), 'directional': check_directional_compose(branches)}


def get_special_sals(stems: List[str], branches: List[str], day_pillar: str) -> Dict[str, Any]:
    day_stem = stems[1]
    day_branch = branches[1]
    month_branch = branches[2]
    yangin_branch = YANGIN_MAP.get(day_stem)
    yangin = [i for i, b in enumerate(branches) if yangin_branch and b == yangin_branch]
    dohwa_branch = DOHWA_MAP.get(day_branch)
    dohwa = [i for i, b in enumerate(branches) if dohwa_branch and b == dohwa_branch and i != 1]
    cheonul_branches = CHEONUL_MAP.get(day_stem, [])
    cheonul = [i for i, b in enumerate(branches) if b in cheonul_branches]
    cheonduk_char = CHEONDUK_MAP.get(month_branch)
    cheonduk = []
    if cheonduk_char:
        cheonduk = [i % 4 for i, ch in enumerate(stems + branches) if ch == cheonduk_char]
        cheonduk = list(dict.fromkeys(cheonduk))
    wolduk_char = WOLDUK_MAP.get(month_branch)
    wolduk = [i for i, s in enumerate(stems) if wolduk_char and s == wolduk_char]
    munchang_branch = MUNCHANG_MAP.get(day_stem)
    munchang = [i for i, b in enumerate(branches) if munchang_branch and b == munchang_branch]
    geumyeo_branch = GEUMYEO_MAP.get(day_stem)
    geumyeo = [i for i, b in enumerate(branches) if geumyeo_branch and b == geumyeo_branch]
    return {
        'yangin': yangin,
        'baekho': day_pillar in BAEKHO_PILLARS,
        'goegang': day_pillar in GOEGANG_PILLARS,
        'dohwa': dohwa,
        'cheonul': cheonul,
        'cheonduk': cheonduk,
        'wolduk': wolduk,
        'munchang': munchang,
        'hongyeom': day_pillar in HONGYEOM_PILLARS,
        'geumyeo': geumyeo,
    }


def get_year_ganzi(year: int) -> str:
    return HGANJI[((12 + (year - 1996)) % 60 + 60) % 60]


def get_gongmang(day_ganzi: str) -> List[str]:
    idx = HGANJI.index(day_ganzi) if day_ganzi in HGANJI else -1
    if idx < 0:
        return ['', '']
    return GONGMANG_TABLE[idx // 10]


def sipsin_info(hanja: str) -> Optional[Dict[str, str]]:
    if not hanja or hanja == '?':
        return None
    if hanja == '本元':
        return {'hanja': '本元', 'hangul': '일간', 'en': 'Day Master'}
    r = next((r for r in RELATIONS if r['hanja'] == hanja), None)
    return {'hanja': hanja, 'hangul': r['hangul'] if r else hanja, 'en': SIPSIN_EN.get(hanja, hanja)}


def meteor_info(hanja: str) -> Dict[str, str]:
    if not hanja or hanja == '?':
        return {'hanja': '-', 'hangul': '-', 'en': '-'}
    m = next((m for m in METEORS_12 if m['hanja'] == hanja), None)
    return {'hanja': hanja, 'hangul': m['hangul'] if m else hanja, 'en': METEOR_EN.get(hanja, hanja)}


def spirit_info(hanja: str) -> Dict[str, str]:
    if not hanja or hanja == '?':
        return {'hanja': '-', 'hangul': '-', 'en': '-'}
    s = next((s for s in SPIRITS_12 if s['hanja'] == hanja), None)
    return {'hanja': hanja, 'hangul': s['hangul'] if s else hanja, 'en': SPIRIT_EN.get(hanja, hanja)}


def calculate_saju(input_data: Dict[str, Any]) -> Dict[str, Any]:
    adjusted = adjust_kdt_to_kst(input_data['year'], input_data['month'], input_data['day'], input_data['hour'], input_data['minute'])
    year = adjusted['year']
    month = adjusted['month']
    day = adjusted['day']
    hour = adjusted['hour']
    minute = adjusted['minute']
    gender = input_data['gender']
    is_male = gender == 'M'
    y_p, m_p, d_p, h_p = get_four_pillars(year, month, day, hour, minute, input_data.get('jasiMethod'))
    day_stem = d_p[0]
    stems = [h_p[0], d_p[0], m_p[0], y_p[0]]
    branches = [h_p[1], d_p[1], m_p[1], y_p[1]]
    ganzis = [h_p, d_p, m_p, y_p]
    pillars = []
    for i, ganzi in enumerate(ganzis):
        stem = stems[i]
        branch = branches[i]
        ss_hanja = '本元' if i == 1 else (get_relation(day_stem, stem)['hanja'] if get_relation(day_stem, stem) else '?')
        jeonggi = get_jeonggi(branch)
        bs_hanja = get_relation(day_stem, jeonggi)['hanja'] if get_relation(day_stem, jeonggi) else '?'
        pillars.append({
            'pillar': {'ganzi': ganzi, 'stem': stem, 'branch': branch},
            'stemSipsin': sipsin_info(ss_hanja),
            'branchJeonggi': jeonggi,
            'branchSipsin': sipsin_info(bs_hanja),
            'jigang': get_hidden_stems(branch),
            'unseong': meteor_info(get_twelve_meteor(day_stem, branch)),
            'sinsal': spirit_info(get_twelve_spirit(y_p[1], branch)),
        })
    dw_hour = 12 if input_data.get('unknownTime') else hour
    dw_minute = 0 if input_data.get('unknownTime') else minute
    raw_daewoon = get_daewoon(is_male, year, month, day, dw_hour, dw_minute, input_data.get('jasiMethod'))
    year_branch = y_p[1]
    gongmang_branches = get_gongmang(d_p)
    gm_set = set(gongmang_branches)
    gongmang = {'branches': gongmang_branches, 'pillarIndices': [i for i, b in enumerate(branches) if i != 1 and b in gm_set]}
    daewoon = []
    for i, dw in enumerate(raw_daewoon):
        dw_stem = dw['ganzi'][0]
        dw_branch = dw['ganzi'][1]
        dw_branch_jeonggi = get_jeonggi(dw_branch)
        daewoon.append({
            'index': i + 1,
            'ganzi': dw['ganzi'],
            'startDate': dw['startDate'],
            'age': dw['startDate'].year - year,
            'stemSipsin': sipsin_info(get_relation(day_stem, dw_stem)['hanja'] if get_relation(day_stem, dw_stem) else '?'),
            'branchSipsin': sipsin_info(get_relation(day_stem, dw_branch_jeonggi)['hanja'] if get_relation(day_stem, dw_branch_jeonggi) else '?'),
            'unseong': meteor_info(get_twelve_meteor(day_stem, dw_branch)),
            'sinsal': spirit_info(get_twelve_spirit(year_branch, dw_branch)),
            'isGongmang': dw_branch in gm_set,
        })
    relations = analyze_all_relations(ganzis)
    special_sals = get_special_sals(stems, branches, d_p)
    current_year = datetime.datetime.now().year
    return {
        'input': input_data,
        'pillars': pillars,
        'dayMaster': {'stem': day_stem, 'element': OHAENG.get(day_stem, '?'), 'elementEn': EL_EN.get(OHAENG.get(day_stem, '?'), OHAENG.get(day_stem, '?'))},
        'elements': {k: 0 for k in ['목', '화', '토', '금', '수']},
        'relations': relations,
        'specialSals': special_sals,
        'gongmang': gongmang,
        'daewoon': daewoon,
        'sewoon': [],
        'wolwoon': [],
        'currentYear': current_year,
    }


def build_pillars(saju_pillars: List[Dict[str, Any]], day_stem: str) -> List[Dict[str, Any]]:
    return saju_pillars


def build_relations(raw: Dict[str, Any]) -> Dict[str, Any]:
    pairs = {}
    for key, val in raw['pairs'].items():
        pairs[key] = {
            'stem': [{'type': r['type'], 'typeEn': RELTYPE_EN.get(r['type'], r['type']), 'detail': r.get('detail'), 'detailEn': EL_EN.get(r.get('detail'), r.get('detail')) if r.get('detail') else None} for r in val['stem']],
            'branch': [{'type': r['type'], 'typeEn': RELTYPE_EN.get(r['type'], r['type']), 'detail': r.get('detail'), 'detailEn': EL_EN.get(r.get('detail'), r.get('detail')) if r.get('detail') else None} for r in val['branch']],
        }
    return {'pairs': pairs, 'triple': raw.get('triple', []), 'directional': raw.get('directional', [])}


def build_daewoon(daewoon: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return daewoon


def build_sewoon(day_stem: str, birth_year_branch: str, start_year: int, end_year: int) -> List[Dict[str, Any]]:
    rows = []
    for y in range(start_year, end_year + 1):
        ganzi = get_year_ganzi(y)
        stem = ganzi[0]
        branch = ganzi[1]
        rows.append({
            'year': y,
            'ganzi': ganzi,
            'stem': stem,
            'branch': branch,
            'stemSipsin': sipsin_info(get_relation(day_stem, stem)['hanja'] if get_relation(day_stem, stem) else '?'),
            'branchSipsin': sipsin_info(get_relation(day_stem, get_jeonggi(branch))['hanja'] if get_relation(day_stem, get_jeonggi(branch)) else '?'),
            'unseong': meteor_info(get_twelve_meteor(day_stem, branch)),
            'sinsal': spirit_info(get_twelve_spirit(birth_year_branch, branch)),
        })
    return rows


def build_wolwoon(day_stem: str, birth_year_branch: str, year: int) -> List[Dict[str, Any]]:
    rows = []
    for m in range(1, 13):
        _, _, month_pillar, _, _ = calc_pillar_indices(year, m, 15, 12, 0)
        ganzi = HGANJI[month_pillar]
        stem = ganzi[0]
        branch = ganzi[1]
        rows.append({
            'month': m,
            'ganzi': ganzi,
            'stem': stem,
            'branch': branch,
            'stemSipsin': sipsin_info(get_relation(day_stem, stem)['hanja'] if get_relation(day_stem, stem) else '?'),
            'branchSipsin': sipsin_info(get_relation(day_stem, get_jeonggi(branch))['hanja'] if get_relation(day_stem, get_jeonggi(branch)) else '?'),
            'unseong': meteor_info(get_twelve_meteor(day_stem, branch)),
            'sinsal': spirit_info(get_twelve_spirit(birth_year_branch, branch)),
        })
    return rows


def process_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    result = calculate_saju(input_data)
    elements = {k: 0 for k in ['목', '화', '토', '금', '수']}
    for p in result['pillars']:
        elements[OHAENG.get(p['pillar']['stem'], '-')] = elements.get(OHAENG.get(p['pillar']['stem'], '-'), 0) + 1
        elements[OHAENG.get(p['pillar']['branch'], '-')] = elements.get(OHAENG.get(p['pillar']['branch'], '-'), 0) + 1
    result['elements'] = elements
    day_stem = result['dayMaster']['stem']
    birth_year_branch = result['pillars'][3]['pillar']['branch']
    current_year = result['currentYear']
    sewoon_start = max(input_data['year'], current_year - 5)
    result['relations'] = build_relations(result['relations'])
    result['daewoon'] = build_daewoon(result['daewoon'])
    result['sewoon'] = build_sewoon(day_stem, birth_year_branch, sewoon_start, current_year + 5)
    result['wolwoon'] = build_wolwoon(day_stem, birth_year_branch, current_year)
    return result


def W(s: Any, n: int) -> str:
    return str(s if s is not None else '-').ljust(n)


def WL(s: Any, n: int) -> str:
    return str(s if s is not None else '-').rjust(n)


def DIV(n: int) -> str:
    return '─' * n


def HDIV(n: int) -> str:
    return '═' * n


def ss(info: Optional[Dict[str, Any]]) -> str:
    if not info:
        return '-'
    if info.get('en') == 'Day Master':
        return '[Day Master 일간]'
    return f"{info.get('hangul')}({info.get('hanja')}) · {info.get('en')}"


def ss_short(info: Optional[Dict[str, Any]]) -> str:
    if not info:
        return '-'
    if info.get('en') == 'Day Master':
        return '[日主]'
    return f"{info.get('hangul')} · {info.get('en')}"


def ms(info: Optional[Dict[str, Any]]) -> str:
    if not info or info.get('hanja') == '-':
        return '-'
    return f"{info.get('hangul')}({info.get('hanja')}) · {info.get('en')}"


def ms_short(info: Optional[Dict[str, Any]]) -> str:
    if not info or info.get('hanja') == '-':
        return '-'
    return f"{info.get('hangul')} · {info.get('en')}"


def sp(info: Optional[Dict[str, Any]]) -> str:
    if not info or info.get('hanja') == '-':
        return '-'
    return f"{info.get('hangul')} · {info.get('en')}"


def pillar_name(idx: int) -> str:
    m = [{'ko': '시주', 'en': 'Hour'}, {'ko': '일주', 'en': 'Day'}, {'ko': '월주', 'en': 'Month'}, {'ko': '년주', 'en': 'Year'}]
    return f"{m[idx]['en']} {m[idx]['ko']}"


def format_saju(d: Dict[str, Any]) -> str:
    inp = d['input']
    p = d['pillars']
    dp = [p[i] for i in [3, 2, 1, 0]]
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    g_label = 'Male (남성)' if inp.get('gender') == 'M' else 'Female (여성)'
    name_line = f"Name:           {inp.get('name')}\n" if inp.get('name') else ''
    time_line = 'Birth Time:      Unknown (미상)' if inp.get('unknownTime') else f"Birth Time:      {int(inp.get('hour', 0)):02d}:{int(inp.get('minute', 0)):02d}"
    date_label = f"{MONTHS[inp['month']-1]} {inp['day']}, {inp['year']}"
    WIDE = 68

    lines: List[str] = []
    def ln(text: str) -> None:
        lines.append(text)
    def blk() -> None:
        lines.append('')

    ln(HDIV(WIDE))
    ln('              SAJU READING  ·  사주 (四柱) 분석')
    ln(HDIV(WIDE))
    ln(f"{name_line}Gender:         {g_label}")
    ln(f"Date of Birth:  {date_label}")
    ln(time_line)
    ln(f"Analyzed:       {today}")
    blk()

    ln(f"{DIV(4)} FOUR PILLARS · 사주 4주 (四柱) {DIV(4)}")
    blk()
    COL = 16
    hdr = ['Year 년주(年)', 'Month 월주(月)', 'Day 일주(日)', 'Hour 시주(時)']
    ln('  ' + ''.join(W(h, COL) for h in hdr))
    ln('  ' + DIV(COL * 4))
    rows = [
        ('Pillar  간지', [x['pillar']['ganzi'] for x in dp]),
        ('Stem    천간', [x['pillar']['stem'] for x in dp]),
        ('Branch  지지', [x['pillar']['branch'] for x in dp]),
    ]
    for label, vals in rows:
        ln(f"  {W(label, 14)} {' '.join(W(v, COL) for v in vals)}")
    blk()
    ln(f"  {'Ten God (십성)'.ljust(14)} {' '.join(W(x['stemSipsin']['hangul'] if x['stemSipsin'] else '-', COL) for x in dp)}")
    ln(f"  {' '.ljust(14)} {' '.join(W(x['stemSipsin']['hanja'] if x['stemSipsin'] else '-', COL) for x in dp)}")
    ln(f"  {' '.ljust(14)} {' '.join(W(x['stemSipsin']['en'] if x['stemSipsin'] else '-', COL) for x in dp)}")
    blk()
    ln(f"  {'정기(Jeonggi)'.ljust(14)} {' '.join(W(x['branchJeonggi'], COL) for x in dp)}")
    ln(f"  {'Branch God'.ljust(14)} {' '.join(W(x['branchSipsin']['hangul'] if x['branchSipsin'] else '-', COL) for x in dp)}")
    ln(f"  {'지지십성'.ljust(14)} {' '.join(W(x['branchSipsin']['hanja'] if x['branchSipsin'] else '-', COL) for x in dp)}")
    ln(f"  {' '.ljust(14)} {' '.join(W(x['branchSipsin']['en'] if x['branchSipsin'] else '-', COL) for x in dp)}")
    blk()
    ln(f"  {'Hidden 지장간'.ljust(14)} {' '.join(W(x['jigang'], COL) for x in dp)}")
    blk()
    ln(f"  {'12 Stage 운성'.ljust(14)} {' '.join(W(ms(x['unseong']), COL) for x in dp)}")
    ln(f"  {' '.ljust(14)} {' '.join(W(x['unseong']['hanja'], COL) for x in dp)}")
    ln(f"  {' '.ljust(14)} {' '.join(W(x['unseong']['en'], COL) for x in dp)}")
    blk()
    ln(f"  {'12 Spirit 신살'.ljust(14)} {' '.join(W(ms(x['sinsal']), COL) for x in dp)}")
    ln(f"  {' '.ljust(14)} {' '.join(W(x['sinsal']['en'], COL) for x in dp)}")
    blk()

    ln(f"{DIV(4)} FIVE ELEMENTS · 오행 분포 (五行) {DIV(4)}")
    blk()
    el_order = ['목', '화', '토', '금', '수']
    el_row = '   '.join(f"{EL_EN[e]} {e}: {d['elements'][e]}" for e in el_order)
    ln(f"  {el_row}")
    total = sum(d['elements'][e] for e in el_order)
    bar = ' '.join(f"{EL_EN[e][:2]}{'█' * round((d['elements'][e] / total) * 20) if total else ''}" for e in el_order)
    ln(f"  {bar}")
    ln(f"  Day Master (일간): {d['dayMaster']['stem']} — {d['dayMaster']['elementEn']} ({d['dayMaster']['element']})")
    blk()

    ln(f"{DIV(4)} PILLAR INTERACTIONS · 지지 형충회합 {DIV(4)}")
    blk()
    pair_display = ['2,3', '1,3', '0,3', '1,2', '0,2', '0,1']
    pair_names = {
        '2,3': 'Month ↔ Year  (월년)', '1,3': 'Day ↔ Year   (일년)', '0,3': 'Hour ↔ Year  (시년)',
        '1,2': 'Day ↔ Month  (일월)', '0,2': 'Hour ↔ Month (시월)', '0,1': 'Hour ↔ Day   (시일)',
    }
    any_pair = False
    for key in pair_display:
        val = d['relations']['pairs'].get(key)
        if not val:
            continue
        all_rel = [*(val.get('stem', [])), *(val.get('branch', []))]
        if not all_rel:
            continue
        any_pair = True
        parts = ', '.join(f"{r['type']}({r['typeEn']}){f' → {r['detailEn']}' if r.get('detailEn') else ''}" for r in all_rel)
        ln(f"  {pair_names.get(key, key)}: {parts}")
    if not any_pair:
        ln('  No pairwise interactions found (없음)')
    blk()
    if d['relations'].get('triple'):
        for r in d['relations']['triple']:
            ln(f"  Triple Combine 삼합: {r['type']}({r['detail']})")
        blk()
    if d['relations'].get('directional'):
        for r in d['relations']['directional']:
            ln(f"  Directional 방합: {r['type']}({r['detail']})")
        blk()

    ln(f"{DIV(4)} SPECIAL STARS · 신살 (神煞) {DIV(4)}")
    blk()
    for m in SPECIAL_SAL_META:
        val = d['specialSals'].get(m['key'])
        if m['indexed']:
            presence = ', '.join(pillar_name(i) for i in val) if isinstance(val, list) and val else 'absent'
        else:
            presence = 'present' if val else 'absent'
        ln(f"  {W(m['ko'], 8)} {m['hanja']}  ({m['en'].ljust(28)}) → {presence}")
    blk()

    ln(f"{DIV(4)} VOID BRANCHES · 공망 (空亡) {DIV(4)}")
    blk()
    gb = d['gongmang'].get('branches', [])
    gp = d['gongmang'].get('pillarIndices', [])
    ln(f"  Void branches (공망지): {', '.join(gb) if gb else 'none'}")
    ln(f"  Affected pillars:       {', '.join(pillar_name(i) for i in gp) if gp else 'none'}")
    blk()

    ln(f"{DIV(4)} MAJOR LUCK PERIODS · 대운 (大運) {DIV(4)}")
    blk()
    ln(f"  {'AGE'.ljust(5)} {'GANZI'.ljust(7)} {'STEM GOD (천간십성)'.ljust(30)} {'BRANCH GOD (지지십성)'.ljust(30)} {'12 STAGE'.ljust(18)} {'SPIRIT (신살)'}")
    ln(f"  {DIV(5)} {DIV(7)} {DIV(30)} {DIV(30)} {DIV(18)} {DIV(16)}")
    for dw in d['daewoon']:
        gflag = '★' if dw.get('isGongmang') else ' '
        ln(f"  {WL(dw['age'], 4)}{gflag} {W(dw['ganzi'], 7)} {W(ss_short(dw['stemSipsin']), 30)} {W(ss_short(dw['branchSipsin']), 30)} {W(ms_short(dw['unseong']), 18)} {sp(dw['sinsal'])}")
    ln('  ★ = Gongmang (공망)')
    blk()

    ln(f"{DIV(4)} ANNUAL FORTUNE · 세운 (歲運) {DIV(4)}")
    blk()
    ln(f"  {'YEAR'.ljust(6)} {'GANZI'.ljust(7)} {'STEM GOD'.ljust(26)} {'BRANCH GOD'.ljust(26)} {'12 STAGE'.ljust(16)} {'SPIRIT'}")
    ln(f"  {DIV(6)} {DIV(7)} {DIV(26)} {DIV(26)} {DIV(16)} {DIV(16)}")
    for sw in d['sewoon']:
        marker = '▶' if sw['year'] == d['currentYear'] else ' '
        ln(f"  {marker}{W(sw['year'], 5)} {W(sw['ganzi'], 7)} {W(ss_short(sw['stemSipsin']), 26)} {W(ss_short(sw['branchSipsin']), 26)} {W(ms_short(sw['unseong']), 16)} {sp(sw['sinsal'])}")
    blk()

    ln(f"{DIV(4)} MONTHLY FORTUNE · 월운 (月運) · {d['currentYear']} {DIV(4)}")
    blk()
    ln(f"  {'MTH'.ljust(5)} {'GANZI'.ljust(7)} {'STEM GOD'.ljust(26)} {'BRANCH GOD'.ljust(26)} {'12 STAGE'.ljust(16)} {'SPIRIT'}")
    ln(f"  {DIV(5)} {DIV(7)} {DIV(26)} {DIV(26)} {DIV(16)} {DIV(16)}")
    for ww in d['wolwoon']:
        ln(f"  {W(MONTHS_SHORT[ww['month']-1], 5)} {W(ww['ganzi'], 7)} {W(ss_short(ww['stemSipsin']), 26)} {W(ss_short(ww['branchSipsin']), 26)} {W(ms_short(ww['unseong']), 16)} {sp(ww['sinsal'])}")
    blk()

    ln(HDIV(WIDE))
    return '\n'.join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Saju Analyzer CLI')
    parser.add_argument('--year', type=int, help='Birth year', required=False)
    parser.add_argument('--month', type=int, help='Birth month', required=False)
    parser.add_argument('--day', type=int, help='Birth day', required=False)
    parser.add_argument('--hour', type=int, default=0, help='Birth hour (0-23)')
    parser.add_argument('--minute', type=int, default=0, help='Birth minute (0-59)')
    parser.add_argument('--gender', choices=['M', 'F'], default='M', help='Gender')
    parser.add_argument('--name', default='', help='Name')
    parser.add_argument('--unknown-time', action='store_true', help='Use if birth time is unknown')
    parser.add_argument('--input-file', type=argparse.FileType('r'), help='JSON input file')
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    args = parse_args()
    if args.input_file:
        data = json.load(args.input_file)
    else:
        if args.year is None or args.month is None or args.day is None:
            raise SystemExit('year, month, and day are required unless --input-file is provided.')
        data = {
            'year': args.year,
            'month': args.month,
            'day': args.day,
            'hour': -1 if args.unknown_time else args.hour,
            'minute': 0 if args.unknown_time else args.minute,
            'gender': args.gender,
            'name': args.name,
            'unknownTime': args.unknown_time,
        }
    output = format_saju(process_input(data))
    print(output)


if __name__ == '__main__':
    main()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)

            input_data = {
                'year': data['year'],
                'month': data['month'],
                'day': data['day'],
                'hour': data.get('hour', 0),
                'minute': data.get('minute', 0),
                'gender': data['gender'],
                'name': data.get('name', ''),
                'unknownTime': data.get('unknownTime', False),
            }

            processed = process_input(input_data)
            report_text = format_saju(processed)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'report': report_text}, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}, ensure_ascii=False).encode('utf-8'))

        return
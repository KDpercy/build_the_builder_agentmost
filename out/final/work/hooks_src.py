import datetime
import re
ONES = ['', 'bir', 'iki', 'üç', 'dört', 'beş', 'altı', 'yedi', 'sekiz', 'dokuz']
TENS = ['', 'on', 'yirmi', 'otuz', 'kırk', 'elli', 'altmış', 'yetmiş', 'seksen', 'doksan']
DIG = ['sıfır', 'bir', 'iki', 'üç', 'dört', 'beş', 'altı', 'yedi', 'sekiz', 'dokuz']
MONTHS = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
CUR = [('debtTL', 'Türk Lirası'), ('debtUSD', 'Dolar'), ('debtEUR', 'Euro'), ('debtGBP', 'İngiliz Sterlini')]
UNIT = {'debtTL': ('Türk Lirası', 'lira', 'kuruş'), 'debtUSD': ('dolar', 'dolar', 'sent'),
        'debtEUR': ('euro', 'euro', 'sent'), 'debtGBP': ('İngiliz Sterlini', 'sterlin', 'peni')}


def w3(n):
    h, r = divmod(n, 100)
    t, o = divmod(r, 10)
    s = []
    if h:
        s.append(('' if h == 1 else ONES[h] + ' ') + 'yüz')
    if t:
        s.append(TENS[t])
    if o:
        s.append(ONES[o])
    return ' '.join(s)


def words(n):
    n = int(n)
    if n == 0:
        return 'sıfır'
    parts = []
    for val, name in ((10 ** 9, 'milyar'), (10 ** 6, 'milyon'), (1000, 'bin')):
        q, n = divmod(n, val)
        if q:
            parts.append('bin' if (val == 1000 and q == 1) else w3(q) + ' ' + name)
    if n:
        parts.append(w3(n))
    return ' '.join(parts)


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def money(x, key):
    v = num(x) or 0.0
    cents = int(round(abs(v) * 100))
    whole, frac = divmod(cents, 100)
    full, unit, sub = UNIT[key]
    if frac == 0:
        return words(whole) + ' ' + full
    return words(whole) + ' ' + unit + ' ' + words(frac) + ' ' + sub


def pdate(s):
    try:
        d, m, y = str(s).strip().split('.')
        return datetime.date(int(y), int(m), int(d))
    except Exception:
        return None


def sdate(s):
    d = pdate(s)
    if not d:
        return ''
    return str(d.day) + ' ' + MONTHS[d.month] + ' ' + str(d.year)


def suffix(s):
    d = pdate(s)
    last = words(d.year).split(' ')[-1] if d else 'altı'
    vow = [c for c in last if c in 'aeıioöuü']
    v = vow[-1] if vow else 'ı'
    hv = {'a': 'ı', 'ı': 'ı', 'e': 'i', 'i': 'i', 'o': 'u', 'u': 'u', 'ö': 'ü', 'ü': 'ü'}[v]
    c = 't' if last[-1] in 'fstkçşhp' else 'd'
    return "'" + c + hv + 'r'


def digits(s):
    return ' '.join(DIG[int(c)] for c in str(s) if c.isdigit())


def today():
    try:
        v = globals().get('vars') or {}
        return datetime.date.fromisoformat(str(v.get('now', ''))[:10])
    except Exception:
        return None


def join_names(names):
    if len(names) == 1:
        return names[0]
    return ', '.join(names[:-1]) + ' ve ' + names[-1]


def safe_name(name):
    name = ' '.join(str(name or '').split())
    if len(name) > 30 or len(name.split(' ')) > 4 or any(ch in name for ch in '{}<>[]"'):
        return ''
    return name


def card_label(last4, name):
    name = safe_name(name)
    return 'Sonu ' + digits(last4) + ' ile biten ' + (('"' + name + '" ') if name else '')


def body_of(res):
    if isinstance(res, dict):
        b = res.get('data')
        if isinstance(b, dict):
            return b
    return {}


def failed(res):
    b = body_of(res)
    r = b.get('result') if isinstance(b.get('result'), dict) else {}
    code = str(r.get('returnCode', ''))
    status = res.get('status_code') if isinstance(res, dict) else None
    ok = code == '1' and isinstance(b.get('data'), dict) and str(status or 200) == '200'
    return (not ok), code, status


def cop(word):
    vow = [c for c in word if c in 'aeıioöuüAEIİOÖUÜ']
    v = (vow[-1] if vow else 'ı').lower()
    hv = {'a': 'ı', 'ı': 'ı', 'e': 'i', 'i': 'i', 'o': 'u', 'u': 'u', 'ö': 'ü', 'ü': 'ü'}.get(v, 'ı')
    c = 't' if word[-1:] in 'fstkçşhp' else 'd'
    return "'" + c + hv + 'r'


def fixcop(text):
    return re.sub(r"(\w+)'dir", lambda m: m.group(1) + cop(m.group(1)), text)


def balance_text(d):
    return fixcop(balance_text0(d))


def balance_text0(d):
    t = today()
    last4 = d.get('cardNumberLast4', '')
    name = d.get('productName', '')
    lab = card_label(last4, name)
    blocks = [(k, n, d.get(k)) for k, n in CUR if isinstance(d.get(k), dict) and d.get(k)]
    st, due, nst = pdate(d.get('statementDate')), pdate(d.get('lastPayDate')), pdate(d.get('nextStatementDate'))
    out = []
    if not st:
        out.append(lab + 'kartınızın henüz kesilmiş bir ekstresi olmadığı için ekstre borcunuz bulunmamaktadır.')
        if nst:
            out.append('İlk hesap kesim tarihiniz ' + sdate(d.get('nextStatementDate')) + ' olacak.')
        return ' '.join(out)
    cut_today = bool(t and nst and t == nst)
    due_passed = bool(t and due and t > due and not cut_today)
    if cut_today or due_passed:
        if cut_today:
            out.append('Hesap kesim tarihiniz bugün, ekstreniz saat 00.00 itibarıyla kesilecek.')
        else:
            out.append(lab + 'kartınızın ' + sdate(d.get('lastPayDate')) + ' tarihli son ödeme tarihi geçmiştir.')
        owe, clear = [], []
        for k, n, b in blocks:
            v = num(b.get('totalDebt'))
            if v is not None and v > 0:
                owe.append(n + ' toplam borcunuz ' + money(v, k))
            else:
                clear.append(n)
        if owe:
            out.append((lab + 'kartınıza ait gelecek dönemler dahil ' if cut_today else 'Gelecek dönemler dahil ') + ', '.join(owe) + "'dir.")
        if clear:
            out.append(join_names(clear) + ' borcunuz bulunmamaktadır.')
        if due_passed and str(d.get('automaticPaymentFlag')) == 'Y':
            tl = d.get('debtTL') if isinstance(d.get('debtTL'), dict) else {}
            ra = num(tl.get('remainAutomaticPaymentAmount'))
            if ra and ra > 0:
                out.append('Otomatik ödeme talimatınızdan alınacak kalan tutar ' + money(ra, 'debtTL') + "'dir.")
        return ' '.join(out)
    if str(d.get('statementPaymentStatus')) == 'NO_DEBT':
        s = lab + 'kartınızın ' + sdate(d.get('statementDate')) + ' tarihli ekstresinden borcunuz bulunmamaktadır.'
        tl = d.get('debtTL') if isinstance(d.get('debtTL'), dict) else {}
        g = num(tl.get('totalDebt'))
        if g is not None and g > 0:
            s += ' Gelecek dönemler dahil toplam borcunuz ' + money(g, 'debtTL') + "'dir."
        if due:
            s += ' Son ödeme tarihiniz ' + sdate(d.get('lastPayDate')) + ' olacaktır.'
        return s
    intro = lab + 'kartınıza ait ' + sdate(d.get('statementDate')) + ' tarihinde kesilen ekstre '
    first = True
    clear = []
    for k, n, b in blocks:
        rd, rm = num(b.get('remainingDebt')) or 0.0, num(b.get('remainingMinPayment')) or 0.0
        sd, mp = num(b.get('statementDebt')) or 0.0, num(b.get('minPayment')) or 0.0
        if rd <= 0:
            clear.append(n)
            continue
        if k == 'debtTL':
            if rm > 0 and rm >= mp:
                s = 'Türk Lirası borcunuz ' + money(sd, k) + ', ödenmesi gereken minimum tutar ' + money(mp, k) + "'dir."
            elif rm <= 0:
                s = 'Türk Lirası borcunuz ' + money(sd, k) + ', kalan toplam borcunuz ' + money(rd, k) + "'dir. Minimum ödemenizi yaptığınız için teşekkür ederiz."
            else:
                s = ('Türk Lirası borcunuz ' + money(sd, k) + ', ödenmesi gereken minimum tutar ' + money(mp, k) +
                     ', kalan toplam borcunuz ' + money(rd, k) + ', kalan minimum ödeme tutarınız ' + money(rm, k) + "'dir.")
        else:
            s = (n + ' borcunuz ' + money(sd, k) + ', kalan toplam borcunuz ' + money(rd, k) +
                 ', ödenmesi gereken minimum tutar ' + money(mp, k) + "'dir.")
        out.append((intro + s) if first else s)
        first = False
    if first:
        out.append(lab + 'kartınızın ' + sdate(d.get('statementDate')) + ' tarihli ekstresinden borcunuz bulunmamaktadır.')
    elif clear:
        out.append(join_names(clear) + ' borcunuz bulunmamaktadır.')
    if due:
        if t and t == due:
            out.append('Borçlarınız için son ödeme tarihiniz bugündür.')
        else:
            out.append('Borçlarınız için son ödeme tarihiniz ' + sdate(d.get('lastPayDate')) + suffix(d.get('lastPayDate')) + '.')
    return ' '.join(out)


FAIL_GENERAL = 'Şu anda işleminizi gerçekleştiremiyorum, sizi müşteri temsilcimize aktarıyorum.'
FAIL_WEEK = 'Şu anda hesap kesim tarihinizi değiştiremiyorum, sizi müşteri temsilcimize aktarıyorum.'


def post(tool, res):
    if not isinstance(res, dict):
        return
    res.pop('header', None)
    b = body_of(res)
    bad, code, status = failed(res)
    d = b.get('data') if isinstance(b.get('data'), dict) else {}
    note = {}
    week_tools = ('statement_week_get', 'statement_week_decide', 'statement_week_change')
    if tool != 'cards_list' and not bad and isinstance(d.get('cards'), list):
        note['durum'] = 'KART_BELIRSIZ'
        note['sonraki_adim'] = ('Hangi kart olduğu kesin değil; hiçbir borç bilgisi söyleme. Söylenen ad birden fazla karta uyuyorsa: '
                                '"[kart adı] isimli birden fazla kartınız var. Kartınızın son dört hanesini söyler misiniz?" '
                                'Son dört hane de birden fazla karta uyuyorsa: "Son dört hanesi [dört hane] olan birden fazla kartınız var. Kartınızın son altı hanesini söyler misiniz?" '
                                'Kart belli olunca cardNumber alanına o kartın kart_kodu_cardNumber değerini yaz (yoksa ilk altı ve son dört haneyi birlikte).')
        res['data'] = {'asistan_notu': note}
        return
    if tool == 'cards_list':
        if bad and (code == 'FB_IVR_CHANNEL_102' or str(status) == '404'):
            note['durum'] = 'UYGUN_KART_YOK'
            note['aynen_soyle'] = 'Ekstre borcunu sorgulayabileceğiniz uygun bir kredi kartınız bulunmuyor. Sizi ana menüye aktarıyorum.'
        elif bad:
            note['durum'] = 'SERVIS_HATASI'
            note['aynen_soyle'] = FAIL_GENERAL
        else:
            cards = [c for c in (d.get('cards') or []) if isinstance(c, dict)]
            lst = []
            for i, c in enumerate(cards):
                same4 = sum(1 for x in cards if x.get('cardNumberLast4') == c.get('cardNumberLast4')) > 1
                samename = sum(1 for x in cards if safe_name(x.get('productName')) == safe_name(c.get('productName'))) > 1
                lst.append({'sira': i + 1, 'kart_kodu_cardNumber': c.get('cardNumber', ''),
                            'kart_adi_veri': safe_name(c.get('productName')) or '(isimsiz: yalnızca son dört hane ile anılır)',
                            'son_dort_hane': c.get('cardNumberLast4', ''),
                            'son_dort_hane_okunus': digits(c.get('cardNumberLast4', '')),
                            'son_alti_hane': str(c.get('cardNumber', ''))[:16].replace('*', '')[-6:] if False else '',
                            'ayni_isimli_baska_kart_var': samename, 'ayni_son_dort_haneli_baska_kart_var': same4,
                            'ana_kart_mi': bool(c.get('isMainCard', True))})
            for x in lst:
                x.pop('son_alti_hane', None)
            try:
                v = globals().get('vars')
                if isinstance(v, dict):
                    v['kart_listesi'] = '|'.join(str(c.get('cardNumber', '')) for c in cards)
            except Exception:
                pass
            note['durum'] = 'TEK_KART' if len(lst) == 1 else 'COKLU_KART'
            note['kartlar'] = lst
            note['kart_sayisi'] = len(lst)
    elif bad:
        if tool == 'statement_pdf_send' and code == 'FB_IVR_CHANNEL_107':
            note['durum'] = 'EKSTRE_BULUNAMADI'
        else:
            note['durum'] = 'SERVIS_HATASI'
        note['aynen_soyle'] = FAIL_WEEK if tool in week_tools else FAIL_GENERAL
        note['sonraki_adim'] = 'Cümleyi aynen söyle; başka hiçbir şey söyleme, başka servis çağırma.'
    elif tool == 'cards_balance':
        note['okunacak_metin'] = balance_text(d)
        note['ekstre_tarihi_statementDate'] = d.get('statementDate', '')
    elif tool == 'statement_week_get':
        wk = d.get('statementWeek')
        try:
            wk = int(wk)
        except Exception:
            wk = 0
        others = [w for w in (1, 2, 3, 4) if w != wk]
        rel = str(d.get('relationType') or '')
        lab = safe_name(d.get('productName'))
        s = (('"' + lab + '" ') if lab else 'Sonu ' + digits(d.get('cardNumberLast4', '')) + ' ile biten ') + 'kartınızın hesap kesim tarihi her ayın ' + str(wk) + '. haftası olarak tanımlı. Bir sonraki hesap kesim tarihiniz ' + sdate(d.get('nextStatementDate')) + ', son ödeme tarihiniz ' + sdate(d.get('nextLastPayDate')) + '.'
        rname = safe_name(d.get('relatedCardProductName')) or 'diğer'
        if rel in ('M', 'C'):
            s += (' Bu kart, sonu ' + digits(str(d.get('relatedCardNumber', ''))[-4:]) + ' ile biten "' + rname + '" kartınızla ortak ekstreye sahiptir; iki kartın hesap kesim haftası, bir sonraki hesap kesim ve son ödeme tarihleri aynıdır.')
        note['okunacak_metin'] = s
        note['mevcut_hafta'] = wk
        note['statementDay'] = d.get('statementDay')
        note['secenek_cumlesi'] = 'Hesap kesim tarihinizi ayın ' + ', '.join(str(w) + '.' for w in others[:-1]) + ' ya da ' + str(others[-1]) + '. haftasına alabilirim. Hangisini tercih edersiniz?'
        note['sunulabilir_haftalar'] = others
        note['okunacak_metin'] = s + ' ' + note['secenek_cumlesi']
        if rel == 'M':
            note['onay_oncesi_cumle'] = 'Bu değişiklik kartınıza bağlı "' + rname + '" kartınızı da etkileyecek.'
        elif rel == 'C':
            note['onay_oncesi_cumle'] = 'Bu değişiklik kartınızın bağlı olduğu "' + rname + '" kartınızı da etkileyecek.'
        else:
            note['onay_oncesi_cumle'] = ''
    elif tool == 'statement_week_decide':
        note['yeni_hesap_kesim_tarihi'] = sdate(d.get('statementDate'))
        note['yeni_son_odeme_tarihi'] = sdate(d.get('statementDueDate'))
        note['sonraki_adim'] = ('Önce varsa onay_oncesi_cumle, sonra: "Yeni hesap kesim haftanız her ayın <hafta>. haftası olacak. Yeni hesap kesim tarihiniz '
                                + sdate(d.get('statementDate')) + ', son ödeme tarihiniz ' + sdate(d.get('statementDueDate')) + ' olacak. Onaylıyor musunuz?"')
    elif tool == 'statement_week_change':
        if str(d.get('exitState')) == 'OK' and str(d.get('responseCode')) == '0':
            note['durum'] = 'DEGISTIRILDI'
            note['sonraki_adim'] = 'Başarı cümlesini önizlemedeki tarihlerle söyle, ardından "Sizi ana menüye yönlendiriyorum."'
        else:
            note['durum'] = 'SERVIS_HATASI'
            note['aynen_soyle'] = FAIL_WEEK
    elif tool == 'contact_email_get':
        em = str(d.get('ibanEmail') or '').strip()
        if em and '@' in em and str(d.get('communicationType')) != 'Phone':
            note['kayitli_eposta_var'] = True
            note['eposta_okunus'] = str(d.get('ttsEmail') or em).strip()
            user = em.split('@')[0]
            if len(user) > 12 or sum(1 for ch in user if not ch.isalpha()) > 1:
                note['eposta_okunus'] = user[0] + ' ile başlayan ' + em.split('@')[1].split('.')[0] + ' adresiniz'
            note['emailAddress_gonderim_icin'] = em
        else:
            note['kayitli_eposta_var'] = False
    elif tool == 'statement_pdf_send':
        if str(d.get('exitState')) == 'DONE':
            note['durum'] = 'GONDERILDI'
            note['sonraki_adim'] = 'Söyle: "Ekstreniz kayıtlı e-posta adresinize gönderildi. Sizi ana menüye yönlendiriyorum."'
        else:
            note['durum'] = 'SERVIS_HATASI'
            note['aynen_soyle'] = FAIL_GENERAL
    res['data'] = {'asistan_notu': note}
    if tool == 'statement_week_get' and not bad:
        res['data']['cardNumber'] = d.get('cardNumber', '')

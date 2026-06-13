"""
Dictionnaire de traductions : classe YOLO COCO → phrase en darija marocaine.
Pour ajouter une nouvelle classe : ajouter une entrée ici.
Les noms de classes correspondent aux labels YOLOv8 COCO (80 classes).
"""

traductions: dict[str, str] = {
    # ── Personnes ──────────────────────────────────────────────────────────────
    'person':        'كاين شي واحد قدامك',

    # ── Véhicules (avertissements prioritaires) ────────────────────────────────
    'car':           'انتبه كاينة طوموبيل',
    'truck':         'انتبه كاين شاحنة',
    'bus':           'كاين طوبيس انتبه',
    'motorcycle':    'انتبه كاينة موتو',
    'bicycle':       'كاين بيسيكلي انتبه',
    'train':         'انتبه كاين قطار',

    # ── Mobilier ──────────────────────────────────────────────────────────────
    'chair':         'كاين كرسي',
    'couch':         'كاين كنابي',
    'bed':           'كاين ليطو',
    'dining table':  'كاينة طابلة',
    'toilet':        'كاين الحمام',
    'bench':         'كاين بنكيو',

    # ── Objets du quotidien ───────────────────────────────────────────────────
    'bottle':        'كاينة قارورة',
    'cup':           'كاين كاس',
    'wine glass':    'كاينة كاس',
    'book':          'كاين كتاب',
    'clock':         'كاينة ساعة',
    'laptop':        'كاين أوردينتور',
    'cell phone':    'كاين تيليفون',
    'tv':            'كاين تيليفيزيون',
    'backpack':      'كاينة شكارة',
    'umbrella':      'كاينة مظلة',
    'handbag':       'كاينة شنطة',
    'suitcase':      'كاينة ولاصة',
    'scissors':      'كاينة مقص',
    'sports ball':   'كاينة كورة',

    # ── Nourriture ────────────────────────────────────────────────────────────
    'banana':        'كاينة بنانة',
    'apple':         'كاينة تفاحة',
    'orange':        'كاين ليمون',
    'pizza':         'كاينة بيتزا',
    'cake':          'كاين كاطو',
    'sandwich':      'كاين ساندويتش',

    # ── Animaux ───────────────────────────────────────────────────────────────
    'dog':           'كاين كلب انتبه',
    'cat':           'كاينة مشة',
    'bird':          'كاين طير',
    'horse':         'كاين عود',
    'cow':           'كاينة بقرة',

    # ── Signalisation ─────────────────────────────────────────────────────────
    'traffic light': 'كاين ضوء انتبه',
    'stop sign':     'كاينة علامة وقف',
}

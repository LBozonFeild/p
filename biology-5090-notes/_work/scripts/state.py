from lib import *
import time
SECS = ["1.1","1.2","3.1","3.2","4.1","5.1","5.2","7.1","7.2","11.1","11.2","11.3","11.4","13.1","13.2",
        "14.1","14.2","14.3","14.4","14.5","14.6","15.1","17.1","17.2","17.3","17.4"]
CHAP = {"1":"CELLS","3":"MOVEMENT INTO AND OUT OF CELLS","4":"BIOLOGICAL MOLECULES","5":"ENZYMES","7":"TRANSPORT IN FLOWERING PLANTS",
        "11":"TRANSPORT IN HUMANS","13":"EXCRETION","14":"COORDINATION AND CONTROL","15":"COORDINATION AND RESPONSE IN PLANTS","17":"INHERITANCE"}
OOS = {"o2":"Classification (syllabus section 2)","o6":"Plant nutrition (section 6)","o8":"Human nutrition (section 8)",
       "o9":"Human gas exchange (section 9)","o10":"Respiration (section 10)","o12":"Disease and immunity (section 12)",
       "o16":"Development of organisms / reproduction / nuclear division (section 16)","o18":"Biotechnology and genetic modification (section 18)",
       "o19":"Organisms and environment / ecology / human impact (section 19)",
       "oX":"Legacy or other topic not in the supplied syllabus list (e.g. support and movement, drugs, kidney dialysis, ADH, growth)"}
def load_dec(): return jload("state/decisions.json")
def save_dec(d): jsave("state/decisions.json", d)
def load_items(): return jload("data/items.json")
def load_pairs(): return jload("state/pairs.json")
def order(): return jload("state/order.json")
def insecs(d): return [s for s in d["sec"].split("+") if s in SECS]
def log(msg):
    with open(os.path.join(W, "state/log.txt"), "a") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
def notes(sec): return open(os.path.join(W, "notes", sec + ".txt"), encoding="utf-8").read()
def save_notes(sec, txt):
    with open(os.path.join(W, "notes", sec + ".txt"), "w", encoding="utf-8") as f: f.write(txt)

from collections import defaultdict, Counter

from bs4 import BeautifulSoup
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, select, Float, Date, Time, join, exists
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy import desc, func
from sqlalchemy.sql import and_
from sqlalchemy import create_engine
import os
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, select, Float, Date, Time, join, exists
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy import desc, func
from sqlalchemy.sql import and_
import spacy
from spacy.matcher import PhraseMatcher
from timeit import default_timer as timer
import arrow
from nltk.stem import SnowballStemmer


class DatabaseHelper():
    def __init__(self):
        self.engine = self.get_engine()
        self.connection = self.engine.connect()
        self.news = self.get_table('news')

    def get_engine(self):
        try:
            print('Development Environment')
            engine = create_engine('postgresql+psycopg2://scrappyuser:password@localhost:5433/scrappy')
        except Exception as e:
            engine = create_engine('postgresql+psycopg2://scrappyuser:aiapaiap@localhost:5432/scrappy')
            print("Production Environment")
        engine = create_engine('postgresql+psycopg2://scrappyuser:password@localhost:5433/scrappy')
        return engine

    def get_table(self, name):
        meta = MetaData()
        table = Table(name, meta, autoload=True, autoload_with=self.engine)
        return table

    def get_articles(self, source):
        st = select([self.news]).where(self.news.c.source == source)
        return self.connection.execute(st)

    def articles_with_position_data(self):
        return select([self.news]).where(and_(self.news.c.article_timestamp >= '2014-07-28', self.news.c.article_timestamp <= '2018-02-23'))


    def fastmarkets_articles(self):
        st = select([self.news]).where(self.news.c.source == 'fastmarkets')
        return self.connection.execute(st)

    def set_fastmarkets_data(self):
        articles = self.fastmarkets_articles()
        for i, a in enumerate(articles):
            if i % 100 == 0:
                print("Processing:", i)
            title, body = self.extract_fast_markets(a.full_html)
            up = self.news.update().values(title=title, full_text=body).where(self.news.c.id == a.id)
            self.connection.execute(up)

    def extract_fast_markets(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find("h1", {'class': 'heading-title'})
        if title is not None:
            title = title.text.strip()
        body = soup.find("div", {'class': 'article-body'})
        if body is not None:
            body = body.text.strip()
        return title, body

    def extract_keywords(self, articles):
        nlp = spacy.load('en_core_web_sm')
        words = defaultdict(lambda: 0)
        others = defaultdict(lambda: 0)
        print("Processing Total", articles.rowcount)
        start = timer()
        for i, f in enumerate(articles):
            if not f.full_text:
                continue
            doc = nlp(f.full_text)
            for token in doc:
                if not token.is_stop and not token.is_punct and token.is_alpha:
                    words[token.lemma_] += 1
                else:
                    others[token.text] += 1
            if i % 100 == 0:
                print("Processed", i)
        end = timer()
        print("Time taken", end - start)
        return words, others

    def extract_mining_com(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('h2', {'class': 'post-headline'})
        if title is not None:
            title = title.text.strip()
        body = soup.find('div', {'class': 'the-post'})
        if body is not None:
            paras = body.find_all('p')
            paras_text = [p.text.strip().replace('\xa0', '') for p in paras]
            body = '\n'.join(paras_text)
        article_el = soup.find('time')
        article_ts = None
        if article_el is not None:
            try:
                v_ts = article_el.get('datetime') or article_el.get('data-unixtime')
                article_ts = arrow.get(v_ts).datetime
            except Exception as e:
                print("Count not parse:", article_el, v_ts)
                article_ts = None
        return title, body, article_ts

    def set_mining_com_data(self, articles=None):
        if not articles:
            articles = self.get_articles('Mining.com - Copper')
        print("Setting Data for {} articles".format(articles.rowcount))
        for i, a in enumerate(articles):
            if i % 100 == 0:
                print("Processing:", i)
            title, body, article_ts = self.extract_mining_com(a.full_html)
            up = self.news.update().values(
                title=title,
                full_text=body,
                article_timestamp=article_ts).where(self.news.c.id == a.id)
            self.connection.execute(up)

    def set_mining_com_authors(self, articles=None):
        for i, a in enumerate(articles):
            if i % 100 == 0:
                print("Processing:", i)
            soup = BeautifulSoup(a.full_html, 'html.parser')
            byline = soup.find('div', {'class': 'post-byline'})
            if not byline:
                print('Skipped', a.id)
                continue
            author = byline.text.split('|')[0]
            up = self.news.update().values(
                author=author
            ).where(
                self.news.c.id == a.id
            )
            self.connection.execute(up)



class SpacyHelper():
    def __init__(self):
        self.nlp = spacy.load('en_core_web_sm')
        self.nlp_tokenizer = spacy.load('en_core_web_sm')
        self.nlp_tokenizer.remove_pipe('tagger')
        self.nlp_tokenizer.remove_pipe('parser')
        self.nlp_tokenizer.remove_pipe('ner')
        self.stemmer = SnowballStemmer('english')

        self.commodities_keywords = {
            'index', 'trading', 'source', 'metal', 'expect', 'mining', 'bulletin', 'import',
            'yuan', 'miner', 'spot',
            'project', 'cobalt', 'government', 'increase', 'market', 'producer', 'base',
            'lithium', 'year', 'iron', 'low',
            'scrap', 'billion', 'week', 'large', 'high', 'report', 'industry', 'percent',
            'trade', 'accord', 'new',
            'grade', 'price', 'demand', 'include', 'lme', 'company', 'country', 'ounce',
            'china', 'contract', 'battery',
            'gold', 'mine', 'investment', 'share', 'nickel', 'time', 'production', 'material',
            'us', 'copper', 'million',
            'lead', 'ore', 'the', 'chinese', 'cost', 'steel', 'operation', 'supply', 'world',
            'aluminium', 'global',
            'month', 'tonne', 'coal', 'add'}

        self.positive_sentiment = {
            'abl', 'abund', 'acclaim', 'accomplish', 'achiev', 'adequ', 'advanc', 'advantag',
            'allianc', 'assur', 'attain', 'attract', 'beauti', 'benefici', 'benefit', 'best',
            'better', 'bolster',
            'boom', 'boost', 'breakthrough', 'brilliant', 'charit', 'collabor', 'compliment',
            'complimentari', 'conclus', 'conduc', 'confid', 'construct',
            'courteous', 'creativ', 'delight', 'depend', 'desir', 'despit', 'destin', 'dilig',
            'distinct', 'dream', 'easi', 'easier', 'easili', 'effect', 'effici',
            'empow', 'enabl', 'encourag', 'enhanc', 'enjoy', 'enthusiasm', 'enthusiast', 'excel',
            'except', 'excit', 'exclus', 'exemplari', 'fantast', 'favor', 'favorit', 'friend',
            'gain', 'good', 'great', 'greater', 'greatest', 'happi', 'happiest', 'happili',
            'highest',
            'honor', 'ideal', 'impress', 'improv', 'incred', 'influenti', 'inform', 'ingenu',
            'innov', 'insight', 'inspir', 'integr', 'invent', 'inventor', 'lead', 'leadership',
            'loyal', 'lucrat', 'meritori', 'opportun', 'optimist', 'outperform', 'perfect',
            'pleas', 'pleasant', 'pleasur', 'plenti', 'popular', 'posit', 'preemin', 'premier',
            'prestig',
            'prestigi', 'proactiv', 'profici', 'profit', 'progress', 'prosper', 'rebound',
            'recept', 'regain', 'resolv', 'revolution', 'reward', 'satisfact',
            'satisfactori', 'satisfactorili', 'satisfi', 'smooth', 'solv', 'spectacular',
            'stabil', 'stabl', 'strength', 'strengthen', 'strong', 'stronger', 'strongest',
            'succeed', 'success', 'superior', 'surpass', 'transpar', 'tremend', 'unmatch',
            'unparallel', 'unsurpass', 'upturn', 'valuabl', 'versatil', 'vibranc', 'vibrant',
            'win', 'winner',
            'worthi'}

        self.negative_sentiment = {
            'abandon', 'abdic', 'aberr', 'abet', 'abnorm', 'abolish', 'abrog', 'abrupt',
            'absenc', 'absente', 'abus', 'accid', 'accident', 'accus', 'acquiesc',
            'acquit', 'acquitt', 'adulter', 'advers', 'adversari', 'aftermath', 'against',
            'aggrav', 'alert', 'alien', 'alleg', 'annoy', 'annul', 'anomal', 'anomali',
            'anticompetit', 'antitrust', 'argu', 'argument', 'arrear', 'arrearag',
            'arrest', 'artifici', 'assault', 'assert', 'attrit', 'avers', 'backdat', 'bad',
            'bail', 'bailout', 'balk', 'ban', 'bankrupt', 'bankruptci', 'bar', 'barrier',
            'bottleneck', 'boycot', 'boycott', 'breach', 'break', 'breakag', 'breakdown',
            'bribe', 'briberi', 'bridg', 'broken', 'burden', 'burdensom', 'burn', 'calam',
            'calamit', 'cancel', 'careless', 'catastroph', 'caution', 'cautionari', 'ceas',
            'censur', 'challeng', 'chargeoff', 'circumv', 'circumvent', 'claim',
            'clawback', 'close', 'closeout', 'closur', 'coerc', 'coercion', 'coerciv',
            'collaps', 'collis', 'collud', 'collus', 'complain', 'complaint', 'complic',
            'compuls', 'conceal', 'conced', 'concern', 'concili', 'condemn', 'condon',
            'confess', 'confin', 'confisc', 'conflict', 'confront', 'confus', 'conspir',
            'conspiraci', 'conspiratori', 'contempt', 'contend', 'content', 'contenti',
            'contest', 'contract', 'contradict', 'contradictori', 'contrari',
            'controversi', 'convict', 'correct', 'corrupt', 'cost', 'counterclaim',
            'counterfeit', 'countermeasur', 'crime', 'crimin', 'crise', 'crisi', 'critic',
            'crucial', 'culpabl', 'cumbersom', 'curtail', 'cut', 'cutback', 'cyberattack',
            'cyberbulli', 'cybercrim', 'cybercrimin', 'damag', 'dampen', 'danger',
            'deadlock', 'deadweight', 'debar', 'deceas', 'deceit', 'deceiv', 'decept',
            'declin', 'defac', 'defam', 'defamatori', 'default', 'defeat', 'defect',
            'defend', 'defens', 'defer', 'defici', 'deficit', 'defraud', 'defunct',
            'degrad', 'delay', 'deleteri', 'deliber', 'delinqu', 'delist', 'demis',
            'demolish', 'demolit', 'demot', 'deni', 'denial', 'denigr', 'deplet', 'deprec',
            'depress', 'depriv', 'derelict', 'derogatori', 'destabil', 'destroy',
            'destruct', 'detain', 'detent', 'deter', 'deterior', 'deterr', 'detract',
            'detriment', 'devalu', 'devast', 'deviat', 'devolv', 'difficult', 'difficulti',
            'diminish', 'diminut', 'disadvantag', 'disaffili', 'disagr', 'disagre',
            'disallow', 'disappear', 'disappoint', 'disapprov', 'disassoci', 'disast',
            'disastr', 'disavow', 'disciplinari', 'disclaim', 'disclos', 'discontinu',
            'discourag', 'discredit', 'discrep', 'disfavor', 'disgorg', 'disgrac',
            'dishonest', 'dishonesti', 'dishonor', 'disincent', 'disinterest',
            'disinterested', 'disloy', 'disloyalti', 'dismal', 'dismiss', 'disord',
            'dispar', 'disparag', 'displac', 'dispos', 'dispossess', 'disproport',
            'disproportion', 'disput', 'disqualif', 'disqualifi', 'disregard', 'disreput',
            'disrupt', 'dissatisfact', 'dissatisfi', 'dissent', 'dissid', 'dissolut',
            'distort', 'distract', 'distress', 'disturb', 'divers', 'divert', 'divest',
            'divestitur', 'divorc', 'divulg', 'doubt', 'downgrad', 'downsiz', 'downtim',
            'downturn', 'downward', 'drag', 'drastic', 'drawback', 'drop', 'drought',
            'duress', 'dysfunct', 'eas', 'egregi', 'embargo', 'embarrass', 'embezzl',
            'encroach', 'encumb', 'encumbr', 'endang', 'endanger', 'enjoin', 'er', 'erod',
            'eros', 'err', 'errat', 'erron', 'error', 'escal', 'evad', 'evas', 'evict',
            'exacerb', 'exagger', 'excess', 'exculp', 'exculpatori', 'exoner', 'exploit',
            'expos', 'expropri', 'expuls', 'extenu', 'fail', 'failur', 'fallout', 'fals',
            'falsif', 'falsifi', 'falsiti', 'fatal', 'fault', 'faulti', 'fear', 'feloni',
            'fictiti', 'fine', 'fire', 'flaw', 'forbid', 'forbidden', 'forc', 'foreclos',
            'foreclosur', 'forego', 'foregon', 'forestal', 'forfeit', 'forfeitur',
            'forger', 'forgeri', 'fraud', 'fraudul', 'frivol', 'frustrat', 'fugit',
            'gratuit', 'grievanc', 'grossli', 'groundless', 'guilti', 'halt', 'hamper',
            'harass', 'hardship', 'harm', 'harsh', 'harsher', 'harshest', 'hazard',
            'hinder', 'hindranc', 'hostil', 'hurt', 'idl', 'ignor', 'ill', 'illeg',
            'illicit', 'illiquid', 'imbal', 'immatur', 'immor', 'impair', 'impass',
            'imped', 'impedi', 'impend', 'imper', 'imperfect', 'imperil', 'impermiss',
            'implic', 'imposs', 'impound', 'impract', 'impractic', 'imprison', 'improp',
            'improprieti', 'imprud', 'inabl', 'inaccess', 'inaccur', 'inaccuraci', 'inact',
            'inactiv', 'inadequ', 'inadequaci', 'inadvert', 'inadvis', 'inappropri',
            'inattent', 'incap', 'incapac', 'incapacit', 'incarcer', 'incid', 'incompat',
            'incompet', 'incomplet', 'inconclus', 'inconsist', 'inconveni', 'incorrect',
            'indec', 'indefeas', 'indict', 'ineffect', 'ineffici', 'inelig', 'inequ',
            'inequit', 'inevit', 'inexperi', 'inexperienc', 'inferior', 'inflict',
            'infract', 'infring', 'inhibit', 'inim', 'injunct', 'injur', 'injuri',
            'inordin', 'inquiri', 'insecur', 'insensit', 'insolv', 'instabl', 'insubordin',
            'insuffici', 'insurrect', 'intent', 'interf', 'interfer', 'intermitt',
            'interrupt', 'intimid', 'intrus', 'invalid', 'investig', 'involuntari',
            'involuntarili', 'irreconcil', 'irrecover', 'irregular', 'irrepar', 'irrevers',
            'jeopard', 'justifi', 'kickback', 'know', 'lack', 'lacklust', 'lag', 'laps',
            'late', 'launder', 'layoff', 'lie', 'limit', 'linger', 'liquid', 'litig',
            'lockout', 'lose', 'loss', 'lost', 'malfeas', 'malfunct', 'malic', 'malici',
            'malpractic', 'manipul', 'markdown', 'misappl', 'misappli', 'misappropri',
            'misbrand', 'miscalcul', 'mischaracter', 'mischief', 'misclassif',
            'misclassifi', 'miscommun', 'misconduct', 'misdat', 'misdemeanor', 'misdirect',
            'mishandl', 'misinform', 'misinterpret', 'misjudg', 'misl', 'mislabel',
            'mislead', 'mismanag', 'mismatch', 'misplac', 'mispric', 'misrepres',
            'misrepresent', 'miss', 'misstat', 'misstep', 'mistak', 'mistaken', 'mistrial',
            'misunderstand', 'misunderstood', 'misus', 'monopol', 'monopoli', 'monopolist',
            'moratoria', 'moratorium', 'mothbal', 'negat', 'neglect', 'neglig',
            'nonattain', 'noncompetit', 'noncompli', 'nonconform', 'nondisclosur',
            'nonfunct', 'nonpay', 'nonperform', 'nonproduc', 'nonproduct', 'nonrecover',
            'nonrenew', 'nuisanc', 'nullif', 'nullifi', 'object', 'objection', 'obscen',
            'obsolesc', 'obsolet', 'obstacl', 'obstruct', 'offenc', 'offend', 'omiss',
            'omit', 'oner', 'opportunist', 'oppos', 'opposit', 'outag', 'outdat', 'outmod',
            'overag', 'overbuild', 'overbuilt', 'overburden', 'overcapac', 'overcharg',
            'overcom', 'overdu', 'overestim', 'overload', 'overlook', 'overpaid',
            'overpay', 'overproduc', 'overproduct', 'overrun', 'overshadow', 'overst',
            'overstat', 'oversuppli', 'overt', 'overturn', 'overvalu', 'panic', 'penal',
            'penalti', 'peril', 'perjuri', 'perpetr', 'persist', 'pervas', 'petti',
            'picket', 'plaintiff', 'plea', 'plead', 'pled', 'poor', 'pose', 'postpon',
            'precipit', 'preclud', 'predatori', 'prejud', 'prejudic', 'prejudici',
            'prematur', 'press', 'pretrial', 'prevent', 'problem', 'problemat', 'prolong',
            'prone', 'prosecut', 'protest', 'protestor', 'protract', 'provok', 'punish',
            'punit', 'purport', 'question', 'quit', 'racket', 'ration', 'reassess',
            'reassign', 'recal', 'recess', 'recessionari', 'reckless', 'redact',
            'redefault', 'redress', 'refus', 'reject', 'relinquish', 'reluct', 'renegoti',
            'renounc', 'repar', 'repossess', 'repudi', 'resign', 'restat', 'restructur',
            'retali', 'retaliatori', 'retribut', 'revoc', 'revok', 'ridicul', 'riski',
            'riskier', 'riskiest', 'sabotag', 'sacrif', 'sacrific', 'sacrifici', 'scandal',
            'scrutin', 'scrutini', 'secreci', 'seiz', 'sentenc', 'serious', 'setback',
            'sever', 'sharpli', 'shock', 'shortag', 'shortfal', 'shrinkag', 'shut',
            'shutdown', 'slander', 'slippag', 'slow', 'slowdown', 'slower', 'slowest',
            'slowli', 'sluggish', 'solvenc', 'spam', 'spammer', 'stagger', 'stagnant',
            'stagnat', 'standstil', 'stolen', 'stop', 'stoppag', 'strain', 'stress',
            'stringent', 'su', 'subject', 'subpoena', 'substandard', 'sue', 'suffer',
            'summon', 'summons', 'suscept', 'suspect', 'suspend', 'suspens', 'suspici',
            'suspicion', 'taint', 'tamper', 'tens', 'termin', 'testifi', 'threat',
            'threaten', 'tighten', 'toler', 'tortuous', 'tragedi', 'tragic', 'traumat',
            'troubl', 'turbul', 'turmoil', 'unabl', 'unaccept', 'unaccount', 'unannounc',
            'unanticip', 'unapprov', 'unattract', 'unauthor', 'unavail', 'unavoid',
            'unawar', 'uncollect', 'uncompetit', 'uncomplet', 'unconscion', 'uncontrol',
            'uncorrect', 'uncov', 'undeliv', 'undeliver', 'undercapit', 'undercut',
            'underestim', 'underfund', 'underinsur', 'undermin', 'underpaid', 'underpay',
            'underperform', 'underproduc', 'underproduct', 'underreport', 'underst',
            'understat', 'underutil', 'undesir', 'undetect', 'undetermin', 'undisclos',
            'undocu', 'undu', 'unduli', 'uneconom', 'unemploy', 'uneth', 'unexcus',
            'unexpect', 'unfair', 'unfavor', 'unfavour', 'unfeas', 'unfit', 'unforese',
            'unforeseen', 'unforseen', 'unfortun', 'unfound', 'unfriend', 'unfulfil',
            'unfund', 'uninsur', 'unintend', 'unintent', 'unjust', 'unjustifi', 'unknow',
            'unlaw', 'unlicens', 'unliquid', 'unmarket', 'unmerchant', 'unmeritori',
            'unnecessari', 'unnecessarili', 'unneed', 'unobtain', 'unoccupi', 'unpaid',
            'unperform', 'unplan', 'unpopular', 'unpredict', 'unproduct', 'unprofit',
            'unqualifi', 'unrealist', 'unreason', 'unrecept', 'unrecov', 'unrecover',
            'unreimburs', 'unreli', 'unremedi', 'unreport', 'unresolv', 'unrest', 'unsaf',
            'unsal', 'unsatisfactori', 'unsatisfi', 'unsavori', 'unschedul', 'unsel',
            'unsold', 'unsound', 'unstabil', 'unstabl', 'unsubstanti', 'unsuccess',
            'unsuit', 'unsur', 'unsuspect', 'unsustain', 'unten', 'untim', 'untrust',
            'untruth', 'unus', 'unwant', 'unwarr', 'unwelcom', 'unwil', 'unwilling',
            'upset', 'urgenc', 'urgent', 'usuri', 'usurp', 'vandal', 'verdict', 'veto',
            'victim', 'violat', 'violenc', 'violent', 'vitiat', 'void', 'volatil',
            'vulner', 'warn', 'wast', 'weak', 'weaken', 'weaker', 'weakest', 'will',
            'worri', 'wors', 'worsen', 'worst', 'worthless', 'writedown', 'writeoff',
            'wrong', 'wrongdo'}

        self.uncertain_sentiment = {
            'abey', 'almost', 'alter', 'ambigu', 'anomal', 'anomali', 'anticip', 'appar',
            'appear', 'approxim', 'arbitrari', 'arbitrarili', 'assum', 'assumpt', 'believ',
            'cautious', 'clarif', 'conceiv', 'condit', 'confus', 'conting', 'could',
            'crossroad', 'depend', 'destabil', 'deviat', 'differ', 'doubt', 'exposur',
            'fluctuat', 'hidden', 'hing', 'imprecis', 'improb', 'incomplet', 'indefinit',
            'indetermin', 'inexact', 'instabl', 'intang', 'likelihood', 'may', 'mayb',
            'might', 'near', 'nonassess', 'occasion', 'ordinarili', 'pend', 'perhap',
            'possibl', 'precaut', 'precautionari', 'predict', 'predictor', 'preliminari',
            'preliminarili', 'presum', 'presumpt', 'probabilist', 'probabl', 'random',
            'reassess', 'recalcul', 'reconsid', 'reexamin', 'reinterpret', 'revis', 'risk',
            'riski', 'riskier', 'riskiest', 'rough', 'rumor', 'seem', 'seldom', 'sometim',
            'somewhat', 'somewher', 'specul', 'sporad', 'sudden', 'suggest', 'suscept',
            'tend', 'tentat', 'turbul', 'uncertain', 'uncertainti', 'unclear', 'unconfirm',
            'undecid', 'undefin', 'undesign', 'undetect', 'undetermin', 'undocu',
            'unexpect', 'unfamiliar', 'unforecast', 'unforseen', 'unguarante', 'unhedg',
            'unidentifi', 'unknown', 'unobserv', 'unplan', 'unpredict', 'unprov',
            'unproven', 'unquantifi', 'unreconcil', 'unseason', 'unsettl', 'unspecif',
            'unspecifi', 'untest', 'unusu', 'unwritten', 'vagari', 'vagu', 'vaguer',
            'vaguest', 'vari', 'variabl', 'varianc', 'variant', 'variat', 'volatil'}



    def create_phrase_matcher(self, word_array, matcher_name):
        term_matchers = list(map(lambda term: self.nlp(term), word_array))
        matcher = PhraseMatcher(self.nlp.vocab)
        matcher.add(matcher_name, None, *term_matchers)
        return matcher


    def match_keywords(self, text):
        # For counting number of keywords in a document
        doc = self.nlp_tokenizer(text)
        lemmas = set([token.lemma_ for token in doc if not token.is_stop and not token.is_punct and token.is_alpha])
        return len(lemmas.intersection(self.commodities_keywords)), len(doc)

    def get_article_sentiment(self, text):
        text = text or ""
        words = text.split()
        article_len = len(words)
        word_set = set()
        for word in words:
            stemmed = self.stemmer.stem(word)
            if stemmed:
                word_set.add(stemmed)

        positive = self.positive_sentiment.intersection(word_set)
        negative = self.negative_sentiment.intersection(word_set)
        uncertain = self.uncertain_sentiment.intersection(word_set)
        return positive, negative, uncertain, article_len




    def find_matches(self, matcher, text):
        if not text:
            return [], 0
        doc = self.nlp(text)
        words = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct and token.is_alpha]
        doc = self.nlp(" ".join(words))
        matches = matcher(doc)
        return len(matches)

    def stem_words(self, word_array):
        # return set of unique stemmed words
        res = set()
        for word in word_array:
            stemmed = self.stemmer.stem(word)
            if stemmed:
                res.add(stemmed)
        return res



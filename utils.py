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
import configparser

class DatabaseHelper():
    def __init__(self):
        self.engine = self.get_engine()
        self.connection = self.engine.connect()
        self.news = self.get_table('news')

    def get_engine(self):
        """
        Create appropriate instance of database engine depending
        on whether in the production or development enviroment
        :return: Database engine
        """
        config = configparser.ConfigParser()
        config.read('/mnt/public/Libs/.pyConfig.ini')
        engine = create_engine('mysql+mysqldb://'+config['mariadbscraper']['user']+':'+config['mariadbscraper']['pass']+'@'+config['mariadbscraper']['host']+':'+config['mariadbscraper']['port']+'/scraperDb?charset=utf8mb4')
        return engine

    def get_table(self, name):
        """
        Return SQLAlchemy representation of a database table
        :param name: name of table
        Example
        db = DatabaseHelper()
        news_table = db.get_table('news')
        # sql statement
        st = select([news_table]).order_by....
        """
        meta = MetaData()
        table = Table(name, meta, autoload=True, autoload_with=self.engine)
        return table

    def get_articles(self, source):
        """
        Helper method for getting articles from a particular source
        :param source: name of source
        :return: SQLAlchemy cursor of articles
        Example
        db = DatabaseHelper()
        articles_cursor = db.get_articles('Mining.com - General')
        for article in articles_cursor:
            # do something here
        """
        st = select([self.news]).where(self.news.c.source == source)
        return self.connection.execute(st)

    def articles_with_position_data(self):
        """
        Helper method for getting subset of articles that position data is availabe for
        :return: SQLAlchemy cursor of articles
        Example
        db = DatabaseHelper()
        articles_cursor = db.articles_with_position_data()
        for article in articles_cursor:
            # do something here
        """
        return select([self.news]).where(and_(self.news.c.article_timestamp >= '2014-07-28', self.news.c.article_timestamp <= '2018-02-23'))

    def articles_without_position_data(self):
        """
        Helper method for getting subset of articles without position data
        :return: SQLAlchemy cursor of articles
        Example
        db = DatabaseHelper()
        articles_cursor = db.articles_without_position_data()
        for article in articles_cursor:
            # do something here
        """
        return select([self.news]).where(self.news.c.article_timestamp > '2018-02-23')

    def fastmarkets_articles(self):
        """
        Helper method for getting subset of articles from fastmarkets
        :return: SQLAlchemy cursor of articles
        Example
        db = DatabaseHelper()
        articles_cursor = db.fastmarkets_articles()
        for article in articles_cursor:
            # do something here
        """
        st = select([self.news]).where(self.news.c.source == 'fastmarkets')
        return self.connection.execute(st)

    def set_fastmarkets_data(self):
        """
        Set title, body and other metadata on articles scraped from fastmarkets
        :return:
        Example
        db = DatabaseHelper()
        db.set_fastmarkets_data()
        """
        articles = self.fastmarkets_articles()
        for i, a in enumerate(articles):
            if i % 100 == 0:
                print("Processing:", i)
            title, body = self.extract_fast_markets(a.full_html)
            up = self.news.update().values(title=title, full_text=body).where(self.news.c.id == a.id)
            self.connection.execute(up)

    def extract_fast_markets(self, html):
        """
        Extracts title, body and other metadata from the html
        scraped from fastmarkets
        :param html:
        :return: title and body
        Example
        db = DatabaseHelper()
        articles = db.fastmarkets_articles()
        for article in articles:
            title, body = db.extract_fast_markets(article.full_html)
            # do something with title and body
        """
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find("h1", {'class': 'heading-title'})
        if title is not None:
            title = title.text.strip()
        body = soup.find("div", {'class': 'article-body'})
        if body is not None:
            body = body.text.strip()
        return title, body

    def get_one_article(self, id):
        """
        Fetch one article by id
        :param id:
        :return: article
        Example
        db = DatabaseHelper()
        article = db.get_one_article(1)
        print(article.title)
        """
        st = select([self.news]).where(self.news.c.id == id)
        res = self.connection.execute(st)
        return res.first()

    def extract_mining_com(self, html):
        """
        Extract title, body and other metadata from html scraped from mining.com
        :param html:
        :return: title, body, article_timestampe and author
        Example
        db = DatabaseHelper()
        articles = db.get_articles('Mining.com - General')
        for article in articles:
            title, body, timestamp, author = db.extract_mining_com(article.full_html)
            # do something with title, body, timestamp, author

        """
        soup = BeautifulSoup(html, 'html.parser')

        # Extract Title
        title = soup.find('h2', {'class': 'post-headline'}) or soup.find('h1', {'class': 'single-title'})
        title = title.text.strip() if title else ""

        # Extract Body Text
        old_format_body = soup.find('div', {'class': 'the-post'})
        try:
            new_format_body = soup.find('div', {'class': 'post-inner-content'}).find('div', {'class': 'col-lg-8'})
        except AttributeError as e:
            new_format_body = None
        if old_format_body:
            paras = old_format_body.find_all('p')
            paras_text = [p.text.strip().replace('\xa0', '') for p in paras]
            body = '\n'.join(paras_text)
        elif new_format_body:
            paras = new_format_body.find_all('p')
            paras_text = [p.text.strip().replace('\xa0', '') for p in paras]
            body = '\n'.join(paras_text)
        else:
            body = ""

        # Extract timestamp
        old_format_time_el = soup.find('time')
        try:
            new_format_time_el = soup.find('article').find('div', {'class': 'post-meta'})
        except AttributeError as e:
            new_format_time_el = None

        if old_format_time_el:
            try:
                v_ts = old_format_time_el.get('datetime') or \
                       old_format_time_el.get('data-unixtime')
                article_ts = arrow.get(v_ts).datetime
            except Exception as e:
                article_ts = None
        elif new_format_time_el:
            try:
                s = list(new_format_time_el.next_elements)[3]
                bits = s.strip().split('|')
                bits = [s.strip() for s in bits]
                ss = (bits[1] + ' ' + bits[2]).strip()
                article_ts = arrow.get(ss, "MMMM D, YYYY H:mm a").datetime
            except Exception as e:
                article_ts = None
        else:
            article_ts = None

        # Extract author
        old_format_byline = soup.find('div', {'class': 'post-byline'})
        try:
            new_format_byline = soup.find('article').find('div', {'class': 'post-meta'}).find('a')
        except AttributeError as e:
            new_format_byline = ""

        if old_format_byline:
            author = old_format_byline.text.split('|')[0] if old_format_byline else ""
        elif new_format_byline:
            author = new_format_byline.text
        else:
            author = ""

        return title, body, article_ts, author

    def set_mining_com_data(self, articles):
        """
        Set the title, author etc for mining.com articles
        :param articles: subset of articles to work on
        Example
        db = DatabaseHelper()
        articles = db.get_articles('Mining.com - General)
        db.set_mining_com_data(articles)
        """
        print("Extracting Data from HTML for {} articles".format(articles.rowcount))
        for i, a in enumerate(articles):
            if i % 100 == 0:
                print("Extracting Data from HTML: {}/{}".format(i, articles.rowcount))
            title, body, article_ts, author = self.extract_mining_com(a.full_html)
            up = self.news.update().values(
                title=title,
                full_text=body,
                article_timestamp=article_ts,
                author=author
            ).where(self.news.c.id == a.id)
            self.connection.execute(up)


class SpacyHelper():
    def __init__(self):
        self.nlp = spacy.load('en_core_web_sm')
        self.nlp_tokenizer = spacy.load('en_core_web_sm')
        self.nlp_tokenizer.remove_pipe('tagger')
        self.nlp_tokenizer.remove_pipe('parser')
        self.nlp_tokenizer.remove_pipe('ner')
        self.stemmer = SnowballStemmer('english')

        # Stemmed words with positive sentiment from the Loughran Macdonald Sentiment Dictionary
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


        # Stemmed words with negative sentiment from the Loughran Macdonald Sentiment Dictionary
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

        # Stemmed words with uncertain sentiment from the Loughran Macdonald Sentiment Dictionary
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


    def get_article_sentiment(self, text):
        """
        Count number of positive, negative and uncertain words that appear in
        a give text
        :param text: text to be processed
        :return: positive, negative and uncertain word counts
        Example
        db = DatabaseHelper()
        s = SpacyHelper()
        article = db.get_article(1)
        positive, negative, uncertain, article_len = s.get_article_sentiment(article.full_text)
        """
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



    def stem_words(self, word_array):
        """
        Used to generate the Positive, Negative and Uncertain stemmed words
        :param word_array: Array of words from the Loughran Macdonald Sentiment Dictionary
        :return: Set of stemmed words
        Example
        s = SpacyHelper()
        words = ['one', 'two', 'three']
        stemmed_words = s.stem_words(word)
        print(stemmed_words)

        """
        res = set()
        for word in word_array:
            stemmed = self.stemmer.stem(word)
            if stemmed:
                res.add(stemmed)
        return res




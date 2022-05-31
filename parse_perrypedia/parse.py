from collections import defaultdict
from html.parser import HTMLParser
from datetime import date
from glob import glob
from typing import List, Dict, Optional, Union

from requests import get
from lxml import etree, html

__author__ = 'Lene Preuss <lene.preuss@gmail.com>'


EPUB_BASE_DIR = '/home/lene/Music/spoken/Literature & Mythology/Perry Rhodan/' \
                'Perry Rhodan Epub Collection 1-2546'
MONTHS = [
    'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
]


def epub_for_novel(novel_number: int) -> str:
    subdir = "{hundreds:02d}{first}-{hundreds:02d}99".format(
        hundreds=(int(novel_number / 100)), first="00" if novel_number > 99 else "01"
    )
    files = glob("{}/{}/{:04d}*.epub".format(EPUB_BASE_DIR, subdir, novel_number))
    return files[0] if files else None


def url_for_novel(novel_number: int) -> str:
    return 'http://www.perrypedia.proc.org/wiki/Quelle:PR{}'.format(novel_number)


def print_xml(element: etree.Element) -> None:
    print(str(etree.tostring(element, pretty_print=True), 'utf-8'))


def extract_linktext(table_cell: etree.Element) -> str:
    return table_cell.find('a').text.replace('\xa0', ' ')


def strip_tags(html: str) -> str:

    class MLStripper(HTMLParser):
        def __init__(self):
            self.reset()
            self.strict = False
            self.convert_charrefs = True
            self.fed = []
            super().__init__()

        def handle_data(self, d):
            self.fed.append(d)

        def get_data(self):
            return ''.join(self.fed)

    s = MLStripper()
    s.feed(html)
    return s.get_data()


SAVE_FILE_NAME = 'novels.pickle'


class PerryRhodanPage:

    pages = []

    @classmethod
    def save(cls, pages: List['PerryRhodanPage'], save_file_name: str = SAVE_FILE_NAME) -> None:
        from pickle import dump
        dump(pages, open(save_file_name, 'wb'))

    @classmethod
    def load(cls, save_file_name: str = SAVE_FILE_NAME) -> List['PerryRhodanPage']:
        from pickle import load
        from os.path import isfile
        return load(open(save_file_name, 'rb')) if isfile(save_file_name) else []

    @classmethod
    def generate(cls, start: int, end: int, verbose: bool = True) -> None:
        cls.pages = cls.load()
        for number in range(max(start, len(cls.pages) + 1), end + 1):
            novel = cls(number)
            cls.pages.append(novel)
            cls.save(cls.pages)
            cls._print_progress(novel, verbose)

    @classmethod
    def _print_progress(cls, novel: 'PerryRhodanPage', verbose: bool):
        if verbose:
            print(novel.number, novel.title, ' ' * 40, end='\r')
            if novel.synopsis:
                print('\n', novel.synopsis)

    @classmethod
    def slice(cls, start: int, end: int) -> List['PerryRhodanPage']:
        if not cls.pages:
            cls.generate(1, end)
        return cls.pages[start - 1:end]

    def __init__(self, novel_number: int):
        self.author: Optional[str] = None
        self.publish_date: Optional[date] = None
        self.cycle: Optional[str] = None
        self.number = novel_number
        html_page = get(url_for_novel(novel_number))
        content = html.fromstring(html_page.text.encode('utf-8')).find('body/div[@id="content"]')
        self.title = self._read_title(content)

        body_content = content.find('div[@id="bodyContent"]')
        self._extract_overview_data(body_content)
        self.synopsis = self._read_synopsis(body_content) or self._read_synopsis_from_epub(self.number)
        self.publisher = 'Pabel-Moewig Verlag KG, Rastatt'

    @property
    def full_title(self) -> str:
        return f'Perry Rhodan {self.number}: {self.title} (Heftroman): Perry Rhodan-Zyklus "{self.cycle}"'

    def goodreads_data(self) -> str:
        return '''Title: {0.full_title}
Author: {0.author}
Published: {0.publish_date}\n'''.format(self) + \
            ('Synopsis: {}\n'.format(self.synopsis) if self.synopsis else '') + \
            'Publisher: {}'.format(self.publisher)

    def _extract_overview_data(self, body_content: etree.Element) -> None:
        for row in self._overview_table_rows(body_content):
            cells = row.findall('td')
            if cells and cells[0] is not None and cells[0].text is not None:
                if 'Autor:' in cells[0].text:
                    self.author = extract_linktext(cells[1])
                elif 'Zyklus:' in cells[0].text:
                    self.cycle = extract_linktext(cells[1])
                elif 'Erstmals' in cells[0].text and 'erschienen' in cells[0].text:
                    self.publish_date = self._extract_date(cells[1])

    @staticmethod
    def _read_title(content: etree.Element) -> str:
        try:
            return content.find('h1/span').text.replace(' (Roman)', '')
        except AttributeError:
            return content.find('h1').text.replace(' (Roman)', '')

    @staticmethod
    def _extract_date(date_cell: etree.Element) -> date:
        cell_text = date_cell.text_content()
        parts = cell_text.strip().split()
        if ',' in parts[0]:
            parts = parts[1:]
        if len(parts) == 3:
            return date(year=int(parts[2]), month=MONTHS.index(parts[1])+1, day=int(parts[0].strip('.')))
        else:
            parts = cell_text.strip().split()
            if len(parts) == 2:
                return date(year=int(parts[1]), month=MONTHS.index(parts[0])+1, day=1)
            else:
                try:
                    return date(year=int(parts[0]), month=12, day=31)
                except ValueError:
                    return None

    @staticmethod
    def _overview_table_rows(body_content: etree.Element) -> List[etree.Element]:
        overview_table = body_content.find('.//div[@class="perrypedia_std_rframe overview"]/table')
        return overview_table.findall('.//tr')

    @staticmethod
    def _read_synopsis(body_content: etree.Element) -> str:
        parse_next_p = False
        for div in body_content.findall('div'):
            for element in div.iter():
                if element.tag == 'h2':
                    span = element.find('span')
                    if span is not None and span.text and 'Kurzzusammenfassung' in span.text:
                        parse_next_p = True
                elif element.tag == 'p' and parse_next_p:
                    return strip_tags(str(etree.tostring(element), 'utf-8')).strip()

    @staticmethod
    def _read_synopsis_from_epub(book_number: int) -> Union[str, None]:
        from ebooklib import epub
        epub_file = epub_for_novel(book_number)
        if epub_file is None:
            return None
        try:
            book = epub.read_epub(epub_file)
        except KeyError:
            return None

        for item in [i for i in book.get_items() if isinstance(i, epub.EpubHtml)]:
            elements = html.fromstring(item.content).xpath('body/p[@class="P-P2"]')
            elements = [e.text for e in elements if e.text is not None and len(e.text) > 10]
            if 1 <= len(elements) <= 20:
                return '\n'.join(elements)

        return None


def count_authors(pages: List[PerryRhodanPage]) -> Dict[str, int]:
    authors = defaultdict(int)
    for page in pages:
        authors[page.author] += 1
    return authors



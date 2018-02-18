#!/usr/bin/env python3
from requests import get
from requests.exceptions import ConnectionError
from lxml import etree, html

from pprint import pprint
from argparse import ArgumentParser, Namespace
from collections import defaultdict
from html.parser import HTMLParser
from sys import argv
from datetime import date
from glob import glob
from typing import List, Dict

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
    return files[0]


def url_for_novel(novel_number: int) -> str:
    return 'http://www.perrypedia.proc.org/wiki/Quelle:PR{}'.format(novel_number)


def print_xml(element: etree.Element) -> None:
    print(str(etree.tostring(element, pretty_print=True), 'utf-8'))


def extract_author(author_cell: etree.Element) -> str:
    return author_cell.find('a').text


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


class PerryRhodanPage:

    SAVE_FILE_NAME = 'novels.pickle'

    pages = []

    @classmethod
    def save(cls, pages: List):
        from pickle import dump
        dump(pages, open(cls.SAVE_FILE_NAME, 'wb'))

    @classmethod
    def load(cls) -> List:
        from pickle import load
        from os.path import isfile
        return load(open(cls.SAVE_FILE_NAME, 'rb')) if isfile(cls.SAVE_FILE_NAME) else []

    @classmethod
    def generate(cls, start: int, end: int) -> None:
        cls.pages = cls.load()
        for number in range(max(start, len(cls.pages) + 1), end + 1):
            try:
                novel = cls(number)
            except ConnectionError:
                novel = cls(number)
            cls.pages.append(cls(number))
            print(number, novel.title, ' ' * 40, end='\r')
        cls.save(cls.pages)

    @classmethod
    def slice(cls, start: int, end: int) -> List:
        if not cls.pages:
            cls.generate(1, end)
        return cls.pages[start - 1:end]

    def __init__(self, novel_number: int):
        self.author = None
        self.publish_date = None
        self.number = novel_number
        html_page = get(url_for_novel(novel_number))
        content = etree.fromstring(html_page.text.encode('utf-8')).find('body/div[@id="content"]')
        self.title = self._read_title(content)

        body_content = content.find('div[@id="bodyContent"]')
        self._extract_overview_data(body_content)
        self.synopsis = self._read_synopsis(body_content) or self._read_synopsis_from_epub(self.number)

    def __str__(self):
        return 'Title: {} (Perry Rhodan, #{})\nAuthor: {}\nPublished: {}\n'.format(
            self.title, self.number, self.author, self.publish_date) + \
            ('Synopsis: {}\n'.format(self.synopsis) if self.synopsis else '') + \
            'Publisher: {}'.format('Pabel-Moewig Verlag KG, Rastatt')

    def _extract_overview_data(self, body_content: etree.Element) -> None:
        for row in self._overview_table_rows(body_content):
            cells = row.findall('td')
            if cells and cells[0] is not None and cells[0].text is not None:
                if 'Autor:' in cells[0].text:
                    self.author = extract_author(cells[1])
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
        parts = date_cell.text.strip().split()
        if ',' in parts[0]:
            parts = parts[1:]
        if len(parts) == 3:
            return date(year=int(parts[2]), month=MONTHS.index(parts[1])+1, day=int(parts[0].strip('.')))
        else:
            parts = date_cell.text.strip().split()
            if len(parts) == 2:
                return date(year=int(parts[1]), month=MONTHS.index(parts[0])+1, day=1)
            else:
                try:
                    return date(year=int(parts[0]), month=12, day=1)
                except ValueError:
                    return None

    @staticmethod
    def _overview_table_rows(body_content: etree.Element) -> List[etree.Element]:
        overview_table = body_content.find('div/div[@class="perrypedia_std_rframe overview"]/table')
        return overview_table.findall('tr')

    @staticmethod
    def _read_synopsis(body_content: etree.Element) -> str:
        parse_next_p = False
        for div in body_content.findall('div'):
            for element in div.iter():
                if element.tag == 'h2':
                    span = element.find('span')
                    if span is not None and 'Kurzzusammenfassung' in span.text:
                        parse_next_p = True
                elif element.tag == 'p' and parse_next_p:
                    return strip_tags(str(etree.tostring(element), 'utf-8')).strip()

    @staticmethod
    def _read_synopsis_from_epub(book_number: int) -> str:
        from ebooklib import epub
        book = epub.read_epub(epub_for_novel(book_number))
        for item in book.get_items():
            if isinstance(item, epub.EpubHtml):
                elements = html.fromstring(item.content).xpath(
                    'x:body/x:p[@class="P-P2"]',
                    namespaces={'x': 'http://www.w3.org/1999/xhtml'}
                )
                for e in elements:
                    print(etree.tostring(e).decode('utf-8'))
        return None


def count_authors(pages: List[PerryRhodanPage]) -> Dict[str, int]:
    authors = defaultdict(int)
    for page in pages:
        authors[page.author] += 1
    return authors


def parse() -> Namespace:
    parser = ArgumentParser(description="Read Perrypedia and print info about Perry Rhodan issues")
    parser.add_argument('-s', '--start', default=1, type=int, help='First issue')
    parser.add_argument('-e', '--end', default=0, type=int, help='Last issue')
    parser.add_argument(
        '-g', '--goodreads', action='store_true', help='Print info required by goodreads'
    )
    return parser.parse_args(argv[1:])


def run(opts: Namespace):
    pages = PerryRhodanPage.slice(opts.start, opts.end if opts.end else opts.start)
    if opts.goodreads:
        for page in pages:
            print(str(page))
    else:
        print(len([page for page in pages if page.synopsis is not None]), 'with synopsis')

        authors = count_authors(pages)
        pprint(sorted([(a[0], a[1]) for a in authors.items()], key=lambda pair: pair[1], reverse=True))

if __name__ == '__main__':
    run(parse())

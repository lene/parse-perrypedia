#!/usr/bin/env python3
__author__ = 'Lene Preuss <lene.preuss@gmail.com>'

from argparse import ArgumentParser, Namespace
from pprint import pprint
from sys import argv

from parse_perrypedia.parse_perrypedia import PerryRhodanPage, count_authors


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
            print(page.goodreads_data())
    else:
        print(len([page for page in pages if page.synopsis is not None]), 'with synopsis')

        authors = count_authors(pages)
        pprint(
            sorted([(a[0], a[1]) for a in authors.items()], key=lambda pair: pair[1], reverse=True))


def main():
    run(parse())


if __name__ == '__main__':
    main()
